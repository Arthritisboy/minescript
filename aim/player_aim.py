import time

import minescript as m

def linear_ease(t: float) -> float:
    """Linear easing for fastest movement"""
    return t

def fast_ease_in_out(t: float) -> float:
    """Very fast easing - minimal smoothing"""
    if t < 0.5:
        return 2.0 * t * t
    else:
        t = 2.0 * t - 1.0
        return 0.5 * (1.0 - (1.0 - t) * (1.0 - t)) + 0.5

def ultra_fast_rotate_to(target_yaw: float, target_pitch: float, duration: float = 0.03, step: float = 0.005):
    """Maximum speed smooth rotation"""
    current_yaw, current_pitch = m.player_orientation()
    
    # Calculate shortest path
    yaw_diff = ((target_yaw - current_yaw + 180) % 360) - 180
    pitch_diff = target_pitch - current_pitch
    
    # Instant for very small angles
    if abs(yaw_diff) < 1.0 and abs(pitch_diff) < 1.0:
        m.player_set_orientation(target_yaw, target_pitch)
        return
    
    steps = max(1, int(duration / step))
    
    for i in range(steps + 1):
        t = i / steps
        y = current_yaw + yaw_diff * t  # Pure linear, no easing
        p = current_pitch + pitch_diff * t
        
        m.player_set_orientation(y % 360.0, p)
        
        if i < steps:
            time.sleep(step)  # Minimal sleep

def hybrid_rotate_to(target_yaw: float, target_pitch: float, fast_threshold: float = 10.0):
    """Hybrid approach: instant for small moves, fast smooth for larger moves"""
    current_yaw, current_pitch = m.player_orientation()
    
    yaw_diff = abs(((target_yaw - current_yaw + 180) % 360) - 180)
    pitch_diff = abs(target_pitch - current_pitch)
    
    if yaw_diff < fast_threshold and pitch_diff < fast_threshold:
        ultra_fast_rotate_to(target_yaw, target_pitch)
    else:
        ultra_fast_rotate_to(target_yaw, target_pitch)