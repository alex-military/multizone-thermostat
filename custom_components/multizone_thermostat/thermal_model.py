"""Advanced Room Thermal Model (SAT) module."""
from collections import deque
import logging
import math
import statistics
import time

_LOGGER = logging.getLogger(__name__)


class ThermalObserver:
    """Observes room temperature to learn thermal capacity, dispersion, and inertia."""

    MIN_COOLING_WINDOW_SECONDS = 1800.0
    MIN_COOLING_DELTA_C = 0.25
    COOLING_REBOUND_CONFIRM_SECONDS = 600.0
    COOLING_REBOUND_DELTA_C = 0.1
    DRAFT_DETECT_MIN_DROP_C = 0.35
    DRAFT_DETECT_MAX_SECONDS = 900.0
    DRAFT_LOCKOUT_SECONDS = 2400.0
    OUTLIER_RATIO_THRESHOLD = 2.5
    COOLING_SAMPLES_MAXLEN = 10
    COOLING_PERCENTILE = 0.35
    MIN_COOLING_R2 = 0.65
    MIN_NEWTON_DELTA_T = 5.0
    MIN_PLAUSIBLE_K_LOSS = 0.001
    MAX_PLAUSIBLE_K_LOSS = 0.25

    MIN_HEATING_WINDOW_SECONDS = 180.0
    MIN_PLAUSIBLE_COOLING_RATE = 0.02
    MAX_PLAUSIBLE_COOLING_RATE = 2.0
    MIN_PLAUSIBLE_HEATING_RATE = 0.05
    MAX_PLAUSIBLE_HEATING_RATE = 10.0
    MAX_PLAUSIBLE_ACTIVE_COOLING_RATE = 10.0

    def __init__(self, zone_id: str, temp_delta_threshold: float = 0.1):
        """Initialize the thermal observer."""
        self.zone_id = zone_id
        self.temp_delta_threshold = temp_delta_threshold

        # State tracking
        self._last_temp = None
        self._last_temp_time = None
        self._is_heating = False
        self._is_cooling_active = False
        self._last_hvac_mode: str | None = None

        # Inertia tracking
        self._temp_at_shutdown = None
        self._shutdown_time = None
        self._max_temp_after_shutdown = None
        self.last_inertia_sample: float = 0.0
        self.last_inertia_event_id: int = 0

        # Sensorless window/draft protection & robust cooling estimation
        self._cooling_samples: deque[float] = deque(maxlen=self.COOLING_SAMPLES_MAXLEN)
        self._k_loss_samples: deque[float] = deque(maxlen=self.COOLING_SAMPLES_MAXLEN)
        self._cooling_window_history: deque[tuple[float, float]] = deque(maxlen=120)
        self._cooling_outdoor_samples: deque[float] = deque(maxlen=120)
        self._pending_cooling_sample: tuple[float, float, float, float | None] | None = None
        self._draft_lockout_until: float = 0.0
        self._prev_cool_temp: float | None = None
        self._prev_cool_time: float | None = None

        # Learned metrics (Exponential Moving Average)
        self.heating_rate = 0.0  # °C / hour
        self.cooling_rate = 0.0  # °C / hour (passive dispersion heat loss)
        self.k_loss = 0.0  # 1 / hour (weather-invariant Newton heat loss coefficient)
        self.active_cooling_rate = 0.0  # °C / hour (active cooling in COOL mode)
        self.thermal_inertia = 0.0  # °C overshoot

    @property
    def is_draft_lockout_active(self) -> bool:
        """Return True when post-draft air/wall re-equilibration lockout is active."""
        return time.monotonic() < self._draft_lockout_until

    def reset_observation(self) -> None:
        """Reset transient tracking baselines without discarding learned thermal metrics."""
        self._last_temp = None
        self._last_temp_time = None
        self._temp_at_shutdown = None
        self._shutdown_time = None
        self._max_temp_after_shutdown = None
        self._pending_cooling_sample = None
        self._prev_cool_temp = None
        self._prev_cool_time = None
        self._cooling_window_history.clear()
        self._cooling_outdoor_samples.clear()

    def _robust_percentile_estimate(self, samples: deque[float]) -> float:
        """Compute 35th-percentile estimate across clean samples."""
        if not samples:
            return 0.0
        vals = sorted(samples)
        if len(vals) == 1:
            return vals[0]
        pos = self.COOLING_PERCENTILE * (len(vals) - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        return vals[lo] + (pos - lo) * (vals[hi] - vals[lo])

    @staticmethod
    def _fit_ols_cooling(samples: list[tuple[float, float]]) -> tuple[float, float] | None:
        """Fit linear cooling trend via OLS and return (rate_c_per_hr, r2) or None."""
        n = len(samples)
        if n < 4:
            return None
        mean_t = sum(t for t, _ in samples) / n
        mean_y = sum(y for _, y in samples) / n
        sxx = sum((t - mean_t) ** 2 for t, _ in samples)
        if sxx <= 0.0:
            return None
        sxy = sum((t - mean_t) * (y - mean_y) for t, y in samples)
        syy = sum((y - mean_y) ** 2 for _, y in samples)
        slope = sxy / sxx  # °C / s (negative for cooling)
        if syy <= 0.0:
            r2 = 0.0
        else:
            r2 = (sxy * sxy) / (sxx * syy)
        return max(0.0, -slope * 3600.0), max(0.0, min(1.0, r2))

    def _commit_cooling_sample(self, rate: float, k_loss_cand: float | None = None) -> bool:
        """Validate, filter asymmetric outliers, and commit a confirmed cooling rate sample."""
        if not (self.MIN_PLAUSIBLE_COOLING_RATE <= rate <= self.MAX_PLAUSIBLE_COOLING_RATE):
            _LOGGER.debug("[%s] Discarded implausible cooling spike: %.2f °C/hr", self.zone_id, rate)
            return False
        if len(self._cooling_samples) >= 3:
            med = statistics.median(self._cooling_samples)
            if med > 0.0 and rate > self.OUTLIER_RATIO_THRESHOLD * med:
                _LOGGER.debug(
                    "[%s] Rejected asymmetric cooling outlier %.2f °C/hr (> %.1fx median %.2f)",
                    self.zone_id,
                    rate,
                    self.OUTLIER_RATIO_THRESHOLD,
                    med,
                )
                return False
        self._cooling_samples.append(rate)
        robust_rate = self._robust_percentile_estimate(self._cooling_samples)
        self._update_ema('cooling_rate', robust_rate, alpha=0.15)

        if (
            k_loss_cand is not None
            and math.isfinite(k_loss_cand)
            and self.MIN_PLAUSIBLE_K_LOSS <= k_loss_cand <= self.MAX_PLAUSIBLE_K_LOSS
        ):
            accept_k = True
            if len(self._k_loss_samples) >= 3:
                med_k = statistics.median(self._k_loss_samples)
                if med_k > 0.0 and k_loss_cand > self.OUTLIER_RATIO_THRESHOLD * med_k:
                    accept_k = False
            if accept_k:
                self._k_loss_samples.append(k_loss_cand)
                robust_k = self._robust_percentile_estimate(self._k_loss_samples)
                self._update_ema('k_loss', robust_k, alpha=0.15)

        _LOGGER.debug(
            "[%s] Cooling rate updated: %.2f °C/hr (raw=%.2f, p35=%.2f, k_loss=%.4f)",
            self.zone_id,
            self.cooling_rate,
            rate,
            robust_rate,
            self.k_loss,
        )
        return True

    def update(
        self,
        current_temp: float,
        is_heating: bool,
        hvac_mode: str | None = None,
        demand: float | None = None,
        window_open: bool = False,
        outdoor_temp: float | None = None,
    ):
        """Update the observer with the latest temperature and state."""
        now = time.monotonic()

        if window_open:
            self.reset_observation()
            self._draft_lockout_until = now + self.DRAFT_LOCKOUT_SECONDS
            self._is_heating = False
            self._is_cooling_active = False
            return

        mode_lower = str(hvac_mode).lower() if hvac_mode is not None else None

        if mode_lower == "cool":
            self._shutdown_time = None
            self._is_heating = False
            self._pending_cooling_sample = None
            self._prev_cool_temp = None
            self._prev_cool_time = None
            self._cooling_window_history.clear()
            self._cooling_outdoor_samples.clear()
            is_cooling_active = bool((demand is not None and demand > 0.0) or is_heating)
            if (
                self._last_temp is None
                or self._last_hvac_mode != "cool"
                or self._is_cooling_active != is_cooling_active
            ):
                self._last_temp = current_temp
                self._last_temp_time = now
                self._last_hvac_mode = "cool"
                self._is_cooling_active = is_cooling_active
                return

            delta_temp = current_temp - self._last_temp
            elapsed_seconds = now - self._last_temp_time
            if abs(delta_temp) >= self.temp_delta_threshold and elapsed_seconds >= self.MIN_HEATING_WINDOW_SECONDS:
                time_elapsed_hours = elapsed_seconds / 3600.0
                if is_cooling_active and delta_temp < 0:
                    if demand is None or demand >= 30.0:
                        duty = max(0.30, min(1.0, float(demand) / 100.0)) if demand is not None else 1.0
                        effective_rate = (abs(delta_temp) / time_elapsed_hours) / duty
                        if self.MIN_PLAUSIBLE_HEATING_RATE <= effective_rate <= self.MAX_PLAUSIBLE_ACTIVE_COOLING_RATE:
                            self._update_ema('active_cooling_rate', effective_rate, alpha=0.1)
                            _LOGGER.debug("[%s] Active cooling rate updated: %.2f °C/hr", self.zone_id, self.active_cooling_rate)
                        else:
                            _LOGGER.debug("[%s] Discarded implausible active cooling rate: %.2f °C/hr", self.zone_id, effective_rate)
                self._last_temp = current_temp
                self._last_temp_time = now
            return

        effective_heating = bool(is_heating and (demand is None or demand >= 10.0))

        if self._last_temp is None or self._last_hvac_mode == "cool":
            self._last_temp = current_temp
            self._last_temp_time = now
            if not effective_heating:
                self._prev_cool_temp = current_temp
                self._prev_cool_time = now
                self._cooling_window_history.append((now, current_temp))
                if outdoor_temp is not None and math.isfinite(outdoor_temp):
                    self._cooling_outdoor_samples.append(float(outdoor_temp))
            self._is_heating = effective_heating
            self._is_cooling_active = False
            self._last_hvac_mode = mode_lower
            return

        self._last_hvac_mode = mode_lower

        if effective_heating:
            self._shutdown_time = None
        elif self._is_heating:
            # Transitioned from active heating to coast-down / low-demand shutdown
            self._temp_at_shutdown = current_temp
            self._shutdown_time = now
            self._max_temp_after_shutdown = current_temp
            _LOGGER.debug("[%s] Heating stopped. Tracking inertia starting from %.2f°C", self.zone_id, current_temp)

        # Update max temp after shutdown (only valid for 60 minutes after shutdown)
        if not effective_heating and self._shutdown_time is not None:
            if now - self._shutdown_time <= 3600:
                if current_temp > self._max_temp_after_shutdown:
                    self._max_temp_after_shutdown = current_temp
                elif current_temp <= self._max_temp_after_shutdown - 0.1:
                    # Peak reached (temperature started dropping)
                    inertia = max(0.0, self._max_temp_after_shutdown - self._temp_at_shutdown)
                    self._update_ema('thermal_inertia', inertia, alpha=0.1)
                    self.last_inertia_sample = inertia
                    self.last_inertia_event_id += 1
                    _LOGGER.debug("[%s] Inertia peak reached: +%.2f°C", self.zone_id, inertia)
                    self._shutdown_time = None
                    self._last_temp = current_temp
                    self._last_temp_time = now
            else:
                inertia = max(0.0, self._max_temp_after_shutdown - self._temp_at_shutdown)
                self._update_ema('thermal_inertia', inertia, alpha=0.1)
                self.last_inertia_sample = inertia
                self.last_inertia_event_id += 1
                _LOGGER.debug("[%s] Inertia window closed: +%.2f°C", self.zone_id, inertia)
                self._shutdown_time = None  # Stop tracking inertia after 1 hour
                self._last_temp = current_temp
                self._last_temp_time = now

        # Reset rate baseline when switching between heating and cooling so durations are not mixed
        if self._is_heating != effective_heating:
            self._last_temp = current_temp
            self._last_temp_time = now
            self._pending_cooling_sample = None
            self._prev_cool_temp = current_temp if not effective_heating else None
            self._prev_cool_time = now if not effective_heating else None
            self._cooling_window_history.clear()
            self._cooling_outdoor_samples.clear()
            self._is_heating = effective_heating
            return

        delta_temp = current_temp - self._last_temp
        elapsed_seconds = now - self._last_temp_time

        if self._is_heating and effective_heating:
            if abs(delta_temp) >= self.temp_delta_threshold and elapsed_seconds >= self.MIN_HEATING_WINDOW_SECONDS:
                time_elapsed_hours = elapsed_seconds / 3600.0
                if delta_temp > 0 and (demand is None or demand >= 30.0):
                    duty = max(0.30, min(1.0, float(demand) / 100.0)) if demand is not None else 1.0
                    effective_rate = (abs(delta_temp) / time_elapsed_hours) / duty
                    if self.MIN_PLAUSIBLE_HEATING_RATE <= effective_rate <= self.MAX_PLAUSIBLE_HEATING_RATE:
                        self._update_ema('heating_rate', effective_rate, alpha=0.1)
                        _LOGGER.debug("[%s] Heating rate updated: %.2f °C/hr", self.zone_id, self.heating_rate)
                    else:
                        _LOGGER.debug("[%s] Discarded implausible heating rate: %.2f °C/hr", self.zone_id, effective_rate)
                self._last_temp = current_temp
                self._last_temp_time = now
        elif not self._is_heating and not is_heating:
            if self._shutdown_time is not None:
                # Wait until post-shutdown inertia settles before measuring passive heat loss
                self._is_heating = effective_heating
                return

            if now < self._draft_lockout_until:
                self._last_temp = current_temp
                self._last_temp_time = now
                self._pending_cooling_sample = None
                self._prev_cool_temp = None
                self._prev_cool_time = None
                self._cooling_window_history.clear()
                self._cooling_outdoor_samples.clear()
                self._is_heating = effective_heating
                return

            # Confirm or reject pending cooling sample via wall thermal rebound check
            if self._pending_cooling_sample is not None:
                cand_rate, cap_temp, cap_ts, cand_k_loss = self._pending_cooling_sample
                if current_temp >= cap_temp + self.COOLING_REBOUND_DELTA_C:
                    _LOGGER.debug(
                        "[%s] Wall thermal rebound (+%.2f°C) after cooling drop: discarding unmonitored window sample and engaging %ds lockout",
                        self.zone_id,
                        current_temp - cap_temp,
                        int(self.DRAFT_LOCKOUT_SECONDS),
                    )
                    self._pending_cooling_sample = None
                    self._draft_lockout_until = now + self.DRAFT_LOCKOUT_SECONDS
                    self._last_temp = current_temp
                    self._last_temp_time = now
                    self._prev_cool_temp = None
                    self._prev_cool_time = None
                    self._cooling_window_history.clear()
                    self._cooling_outdoor_samples.clear()
                    self._is_heating = effective_heating
                    return
                if (now - cap_ts) >= self.COOLING_REBOUND_CONFIRM_SECONDS:
                    self._commit_cooling_sample(cand_rate, k_loss_cand=cand_k_loss)
                    self._pending_cooling_sample = None

            # Fast draft / unmonitored open window detector (sliding short window + baseline check)
            baseline_fast_draft = (
                elapsed_seconds >= 180.0
                and delta_temp <= -self.DRAFT_DETECT_MIN_DROP_C
                and (abs(delta_temp) / (elapsed_seconds / 3600.0)) > self.MAX_PLAUSIBLE_COOLING_RATE
            )
            short_fast_draft = False
            if (
                self._prev_cool_temp is None
                or self._prev_cool_time is None
                or current_temp > self._prev_cool_temp
                or (now - self._prev_cool_time) > self.DRAFT_DETECT_MAX_SECONDS
            ):
                self._prev_cool_temp = current_temp
                self._prev_cool_time = now
            else:
                short_dt = now - self._prev_cool_time
                short_drop = self._prev_cool_temp - current_temp
                if (
                    short_dt >= 180.0
                    and short_drop >= self.DRAFT_DETECT_MIN_DROP_C
                    and (short_drop / (short_dt / 3600.0)) > self.MAX_PLAUSIBLE_COOLING_RATE
                ):
                    short_fast_draft = True

            if baseline_fast_draft or short_fast_draft:
                _LOGGER.debug(
                    "[%s] Fast unmonitored draft detected: engaging %ds lockout",
                    self.zone_id,
                    int(self.DRAFT_LOCKOUT_SECONDS),
                )
                self._pending_cooling_sample = None
                self._draft_lockout_until = now + self.DRAFT_LOCKOUT_SECONDS
                self._last_temp = current_temp
                self._last_temp_time = now
                self._prev_cool_temp = None
                self._prev_cool_time = None
                self._cooling_window_history.clear()
                self._cooling_outdoor_samples.clear()
                self._is_heating = effective_heating
                return

            if delta_temp > 0:
                # Passive warming (sun/occupants): shift baseline upward without corrupting cooling window
                self._last_temp = current_temp
                self._last_temp_time = now
                self._prev_cool_temp = current_temp
                self._prev_cool_time = now
                self._cooling_window_history.clear()
                self._cooling_outdoor_samples.clear()
            else:
                if self._cooling_window_history and now <= self._cooling_window_history[-1][0]:
                    self._cooling_window_history[-1] = (now, current_temp)
                else:
                    self._cooling_window_history.append((now, current_temp))
                if outdoor_temp is not None and math.isfinite(outdoor_temp):
                    self._cooling_outdoor_samples.append(float(outdoor_temp))

                if delta_temp <= -self.MIN_COOLING_DELTA_C and elapsed_seconds >= self.MIN_COOLING_WINDOW_SECONDS:
                    ols_res = self._fit_ols_cooling(list(self._cooling_window_history))
                    if ols_res is not None:
                        ols_rate, r2 = ols_res
                        if r2 < self.MIN_COOLING_R2:
                            _LOGGER.debug(
                                "[%s] Discarded non-linear cooling window (R2=%.2f < %.2f)",
                                self.zone_id,
                                r2,
                                self.MIN_COOLING_R2,
                            )
                            self._cooling_window_history.clear()
                            self._cooling_outdoor_samples.clear()
                            self._last_temp = current_temp
                            self._last_temp_time = now
                            self._prev_cool_temp = current_temp
                            self._prev_cool_time = now
                            self._is_heating = effective_heating
                            return
                        rate = ols_rate
                    else:
                        rate = abs(delta_temp) / (elapsed_seconds / 3600.0)

                    k_loss_cand = None
                    if self._cooling_outdoor_samples:
                        avg_out = sum(self._cooling_outdoor_samples) / len(self._cooling_outdoor_samples)
                        avg_in = 0.5 * (self._last_temp + current_temp)
                        dt_ext = avg_in - avg_out
                        if dt_ext >= self.MIN_NEWTON_DELTA_T:
                            k_loss_cand = rate / dt_ext

                    if self.MIN_PLAUSIBLE_COOLING_RATE <= rate <= self.MAX_PLAUSIBLE_COOLING_RATE:
                        self._pending_cooling_sample = (rate, current_temp, now, k_loss_cand)
                    else:
                        _LOGGER.debug("[%s] Discarded implausible cooling spike: %.2f °C/hr", self.zone_id, rate)
                        self._pending_cooling_sample = None
                        self._draft_lockout_until = now + self.DRAFT_LOCKOUT_SECONDS
                    self._cooling_window_history.clear()
                    self._cooling_outdoor_samples.clear()
                    self._cooling_window_history.append((now, current_temp))
                    if outdoor_temp is not None and math.isfinite(outdoor_temp):
                        self._cooling_outdoor_samples.append(float(outdoor_temp))
                    self._last_temp = current_temp
                    self._last_temp_time = now
                    self._prev_cool_temp = current_temp
                    self._prev_cool_time = now

        self._is_heating = effective_heating

    def _update_ema(self, attribute: str, new_value: float, alpha: float = 0.1):
        """Update Exponential Moving Average."""
        current_value = getattr(self, attribute)
        if current_value == 0.0:
            setattr(self, attribute, new_value)
        else:
            setattr(self, attribute, (alpha * new_value) + ((1.0 - alpha) * current_value))

    def dump_state(self) -> dict:
        """Dump the learned metrics for storage."""
        return {
            "heating_rate": self.heating_rate,
            "cooling_rate": self.cooling_rate,
            "k_loss": self.k_loss,
            "active_cooling_rate": self.active_cooling_rate,
            "thermal_inertia": self.thermal_inertia,
            "cooling_samples": [round(s, 4) for s in self._cooling_samples],
            "k_loss_samples": [round(s, 6) for s in self._k_loss_samples],
        }

    def load_state(self, state: dict):
        """Load learned metrics from storage, sanitizing legacy corrupted spikes."""
        if not isinstance(state, dict):
            return
        try:
            hr = float(state.get("heating_rate", 0.0) or 0.0)
        except (ValueError, TypeError):
            hr = 0.0
        if not math.isfinite(hr) or hr < 0.0 or hr > self.MAX_PLAUSIBLE_HEATING_RATE:
            _LOGGER.info("[%s] Resetting out-of-range stored heating_rate (%s) to 0.0", self.zone_id, hr)
            hr = 0.0
        self.heating_rate = hr

        try:
            cr = float(state.get("cooling_rate", 0.0) or 0.0)
        except (ValueError, TypeError):
            cr = 0.0
        if not math.isfinite(cr) or cr < 0.0 or cr > self.MAX_PLAUSIBLE_COOLING_RATE:
            _LOGGER.info("[%s] Resetting out-of-range stored cooling_rate (%s) to 0.0", self.zone_id, cr)
            cr = 0.0
        self.cooling_rate = cr

        self._cooling_samples.clear()
        if cr > 0.0:
            raw_samples = state.get("cooling_samples", [])
            if isinstance(raw_samples, list):
                valid_samples = []
                for s in raw_samples:
                    try:
                        val = float(s)
                    except (ValueError, TypeError):
                        continue
                    if math.isfinite(val) and self.MIN_PLAUSIBLE_COOLING_RATE <= val <= self.MAX_PLAUSIBLE_COOLING_RATE:
                        valid_samples.append(val)
                self._cooling_samples.extend(valid_samples[-self.COOLING_SAMPLES_MAXLEN:])

        try:
            kl = float(state.get("k_loss", 0.0) or 0.0)
        except (ValueError, TypeError):
            kl = 0.0
        if not math.isfinite(kl) or kl < 0.0 or kl > self.MAX_PLAUSIBLE_K_LOSS:
            _LOGGER.info("[%s] Resetting out-of-range stored k_loss (%s) to 0.0", self.zone_id, kl)
            kl = 0.0
        self.k_loss = kl

        self._k_loss_samples.clear()
        if kl > 0.0:
            raw_k = state.get("k_loss_samples", [])
            if isinstance(raw_k, list):
                valid_k = []
                for s in raw_k:
                    try:
                        val = float(s)
                    except (ValueError, TypeError):
                        continue
                    if math.isfinite(val) and self.MIN_PLAUSIBLE_K_LOSS <= val <= self.MAX_PLAUSIBLE_K_LOSS:
                        valid_k.append(val)
                self._k_loss_samples.extend(valid_k[-self.COOLING_SAMPLES_MAXLEN:])

        try:
            acr = float(state.get("active_cooling_rate", 0.0) or 0.0)
        except (ValueError, TypeError):
            acr = 0.0
        if not math.isfinite(acr) or acr < 0.0 or acr > self.MAX_PLAUSIBLE_ACTIVE_COOLING_RATE:
            _LOGGER.info("[%s] Resetting out-of-range stored active_cooling_rate (%s) to 0.0", self.zone_id, acr)
            acr = 0.0
        self.active_cooling_rate = acr

        try:
            ti = float(state.get("thermal_inertia", 0.0) or 0.0)
        except (ValueError, TypeError):
            ti = 0.0
        if not math.isfinite(ti) or ti < 0.0:
            ti = 0.0
        self.thermal_inertia = ti

    def get_weather_multiplier(self, manual_base_curve: float = 0.0) -> float:
        """
        Calculate the weather compensation multiplier (Ke) based on thermal metrics.
        Returns 0.0 when weather compensation is disabled (manual_base_curve <= 0).
        """
        if manual_base_curve <= 0.0:
            return 0.0

        if self.heating_rate > 0.1 and self.cooling_rate > 0.01:
            # Dispersion ratio normalized around typical baseline (~0.15) to bend +/- 50%
            adaptive_curve = self.cooling_rate / self.heating_rate
            bend_factor = max(0.5, min(1.5, adaptive_curve / 0.15))
            return manual_base_curve * bend_factor
            
        return manual_base_curve
