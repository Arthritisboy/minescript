from visibility_scanner.scanner import scan_targets, scan_target
from visibility_scanner.world_scanners import get_area, get_line
import aim.player_aim

import threading
import time
import math
import random

import minescript as m


target_ids = [
    "minecraft:nether_quartz_ore",
    "minecraft:ancient_debris",
    "minecraft:nether_gold_ore"
]

reach = 4.8
previous_target = m.player_position()

# Global flag to control the mining loop
mining_active = True
recently_mined_positions = set()  # Track recently mined positions to avoid repeats
original_y_level = None  # Track original Y level
fall_recovery_active = False  # Track if we're in fall recovery mode
last_y_check_time = 0
y_check_interval = 0.5  # Check Y level every 0.5 seconds

def wait_ticks(ticks):
    """Wait for specified number of Minecraft ticks (20 ticks = 1 second)"""
    if not mining_active:
        return False
    start_time = time.time()
    target_time = start_time + (ticks / 20.0)
    while mining_active and time.time() < target_time:
        if check_for_t_press():
            return False
        time.sleep(0.01)  # Small sleep to prevent CPU overload
    return mining_active

def stop_mining():
    global mining_active
    mining_active = False

def check_for_t_press():
    """Check if T key is pressed to stop mining"""
    screen = m.screen_name()
    if screen and "chat" in screen.lower():
        
        stop_mining()
        return True
    return False

def gravel_check(yaw, pitch):
    """Ultra-fast gravel check with instant rotation"""
    if not mining_active:
        return False
        
    aim.player_aim.ultra_fast_rotate_to(yaw, pitch)
    
    targeted_block = m.player_get_targeted_block(max_distance=5)
    
    if targeted_block and targeted_block.type:
        is_gravel = "gravel" in targeted_block.type.lower()
        return is_gravel
    return False


def gravel_mine():
    """ULTRA-FAST gravel handling using ticks"""
    if not mining_active:
        return
    
    m.player_press_forward(False)
    # Switch to shovel (hotbar slot 9)
    m.press_key_bind("key.hotbar.9", True)
    wait_ticks(1)  # 1 tick = 0.05 seconds
    m.press_key_bind("key.hotbar.9", False)
    
    # Mine quickly
    m.player_press_attack(True)
    wait_ticks(20)  # 20 ticks = 1 second
    m.player_press_attack(False)
    
    # Switch back to pickaxe (hotbar slot 1)
    if mining_active:
        m.press_key_bind("key.hotbar.1", True)
        wait_ticks(1)  # 1 tick = 0.05 seconds
        m.press_key_bind("key.hotbar.1", False)
        m.player_press_forward(True)

def check_for_basalt_or_blackstone():
    """Check if basalt or blackstone is detected in the DIRECT mining path"""
    if not mining_active:
        return False
    
    # Get player position and orientation
    px, py, pz = m.player_position()
    yaw, pitch = m.player_orientation()
    facing_direction = get_facing_direction(yaw)
    
    # Check ONLY the blocks directly in the mining path (where the player is looking/mining)
    check_positions = []
    
    # Check 2-3 blocks directly ahead in the mining direction (the actual mining area)
    if facing_direction == "north":  # -Z
        for distance in range(2, 4):  # Check 2-3 blocks ahead
            check_positions.append((int(px), int(py), int(pz - distance)))      # Body level
            check_positions.append((int(px), int(py + 1), int(pz - distance)))  # Head level
    elif facing_direction == "south":  # +Z
        for distance in range(2, 4):
            check_positions.append((int(px), int(py), int(pz + distance)))
            check_positions.append((int(px), int(py + 1), int(pz + distance)))
    elif facing_direction == "east":  # +X
        for distance in range(2, 4):
            check_positions.append((int(px + distance), int(py), int(pz)))
            check_positions.append((int(px + distance), int(py + 1), int(pz)))
    elif facing_direction == "west":  # -X
        for distance in range(2, 4):
            check_positions.append((int(px - distance), int(py), int(pz)))
            check_positions.append((int(px - distance), int(py + 1), int(pz)))
    
    # Remove duplicates
    check_positions = list(set(check_positions))
    
    # Check each position for basalt or blackstone
    for check_x, check_y, check_z in check_positions:
        block_type = m.getblock(check_x, check_y, check_z)
        if block_type and ("basalt" in block_type.lower() or "blackstone" in block_type.lower()):
            return True
    
    return False

def only_netherrack_in_mining_path():
    """Check if only netherrack is detected in the DIRECT mining path"""
    if not mining_active:
        return False
    
    # Get player position and orientation
    px, py, pz = m.player_position()
    yaw, pitch = m.player_orientation()
    facing_direction = get_facing_direction(yaw)
    
    # Check ONLY the blocks directly in the mining path
    check_positions = []
    
    # Check 2-3 blocks directly ahead in the mining direction
    if facing_direction == "north":  # -Z
        for distance in range(2, 4):
            check_positions.append((int(px), int(py), int(pz - distance)))
            check_positions.append((int(px), int(py + 1), int(pz - distance)))
    elif facing_direction == "south":  # +Z
        for distance in range(2, 4):
            check_positions.append((int(px), int(py), int(pz + distance)))
            check_positions.append((int(px), int(py + 1), int(pz + distance)))
    elif facing_direction == "east":  # +X
        for distance in range(2, 4):
            check_positions.append((int(px + distance), int(py), int(pz)))
            check_positions.append((int(px + distance), int(py + 1), int(pz)))
    elif facing_direction == "west":  # -X
        for distance in range(2, 4):
            check_positions.append((int(px - distance), int(py), int(pz)))
            check_positions.append((int(px - distance), int(py + 1), int(pz)))
    
    # Remove duplicates
    check_positions = list(set(check_positions))
    
    # Check if ALL detected blocks in mining path are netherrack (or air)
    for check_x, check_y, check_z in check_positions:
        block_type = m.getblock(check_x, check_y, check_z)
        if block_type and block_type != "minecraft:air":
            if "netherrack" not in block_type.lower() and "air" not in block_type.lower():
                return False
    
    return True

def handle_basalt_blackstone_mining():
    """Handle mining when basalt or blackstone is detected - WITH ORE SCANNING AND SIMPLE STUCK DETECTION"""
    global mining_active
    
    m.echo("🔍 Checking mining path for basalt/blackstone...")
    
    # Start sneaking if basalt/blackstone detected
    if check_for_basalt_or_blackstone():
        if not m.player_press_sneak(True):
            m.echo("🪨 Basalt/Blackstone detected! Starting sneak mining...")
            m.player_press_sneak(True)
            time.sleep(0.2)  # Allow sneak to engage
        
        # SAVE the original mining orientation at the start of basalt/blackstone mode
        original_yaw, original_pitch = m.player_orientation()
        m.echo(f"💾 Saved mining orientation: yaw={original_yaw:.1f}, pitch={original_pitch:.1f}")
        
        # Continue mining while sneaking and monitoring block changes
        netherrack_only_start = None
        last_check_time = time.time()
        check_interval = 0.5  # Check every 0.5 seconds
        
        # ADDED: Ore check variables
        last_ore_check_time = time.time()
        ore_check_interval = 3.0  # Check for ores every 3 seconds
        
        # ADDED: Simple stuck detection variables for basalt/blackstone mode
        movement_check_start = time.time()
        last_position = m.player_position()
        consecutive_stuck_checks = 0
        stuck_threshold = 3
        
        while mining_active:
            if check_for_t_press():
                break
                
            current_time = time.time()
            
            # ADDED: Regular ore checking during basalt/blackstone mining
            if current_time - last_ore_check_time >= ore_check_interval:
                last_ore_check_time = current_time
                m.echo("💎 Checking for ores during basalt/blackstone mining...")
                
                # Save current orientation before ore mining
                pre_ore_yaw, pre_ore_pitch = m.player_orientation()
                
                if ore_check():
                    m.echo("✅ Ore mined during basalt/blackstone mode, returning to mining orientation...")
                    
                    # RETURN TO ORIGINAL MINING ORIENTATION after ore mining
                    aim.player_aim.hybrid_rotate_to(original_yaw, original_pitch, fast_threshold=15.0)
                    time.sleep(0.2)
                    m.echo("🔄 Returned to mining orientation")
                    
                    # Reset the netherrack timer and stuck detection since we moved for ore mining
                    netherrack_only_start = None
                    last_position = m.player_position()
                    movement_check_start = current_time
                    consecutive_stuck_checks = 0
            
            # ADDED: Simple stuck detection during basalt/blackstone mining
            if current_time - movement_check_start >= 5:
                current_pos = m.player_position()
                distance_moved = math.sqrt(
                    (current_pos[0] - last_position[0])**2 + 
                    (current_pos[2] - last_position[2])**2
                )
                
                if distance_moved < 0.3:
                    consecutive_stuck_checks += 1
                    m.echo(f"⚠️ Stuck detection in basalt mode: {consecutive_stuck_checks}/{stuck_threshold}")
                    
                    if distance_moved == 0.00 or consecutive_stuck_checks >= stuck_threshold:
                        m.echo("🚫 Stuck in basalt/blackstone mode! Simple recovery: moving forward...")
                        
                        # SIMPLE RECOVERY: Just move forward a bit
                        m.player_press_forward(True)
                        time.sleep(1.0)  # Move forward for 1 second
                        
                        # Reset stuck detection
                        last_position = m.player_position()
                        movement_check_start = time.time()
                        consecutive_stuck_checks = 0
                        m.echo("✅ Simple recovery completed, continuing basalt/blackstone mining")
                else:
                    consecutive_stuck_checks = 0
                
                last_position = current_pos
                movement_check_start = current_time
            
            if current_time - last_check_time >= check_interval:
                last_check_time = current_time
                
                # Check if we're still in basalt/blackstone mode
                if check_for_basalt_or_blackstone():
                    m.player_press_forward(True)
                    time.sleep(0.2)
                    # Reset timer if basalt/blackstone is detected again
                    netherrack_only_start = None
                    m.echo("🔄 Still mining basalt/blackstone - keeping sneak on")
                else:
                    # Start timer if only netherrack is detected
                    if only_netherrack_in_mining_path():
                        if netherrack_only_start is None:
                            netherrack_only_start = current_time
                            m.echo("✅ Only netherrack detected, starting 2-second timer...")
                        elif current_time - netherrack_only_start >= 2.0:
                            m.echo("✅ 2 seconds of only netherrack - stopping sneak")
                            m.player_press_sneak(False)
                            time.sleep(0.2)  # Allow sneak to disengage
                            return True  # Exit basalt/blackstone mode
                    else:
                        # Reset timer if something other than netherrack is detected
                        netherrack_only_start = None
                
                # CONTINUOUS FALL DETECTION CHECK
                current_yaw, current_pitch = m.player_orientation()
                if not monitor_fall_continuously(current_yaw, current_pitch):
                    # Fall recovery handled, reset stuck detection
                    last_position = m.player_position()
                    movement_check_start = time.time()
                    consecutive_stuck_checks = 0
                    m.echo("🔄 Reset stuck detection after fall recovery in basalt mode")
                
                # LAVA CHECK
                if check_for_lava():
                    m.echo("LAVA DETECTED! Stopping strip mining.")
                    m.player_press_forward(False)
                    m.player_press_sneak(False)
                    emergency_lava_stop()
                    return False
            
            # Continue mining at SAVED orientation (not current orientation)
            mine_at_angle(original_yaw, original_pitch, True)
            
            # Small delay to prevent CPU overload
            time.sleep(0.1)
    
    # If we exit the loop, ensure sneak is released
    if m.player_press_sneak(True):
        m.player_press_sneak(False)
        time.sleep(0.2)
    
    return False

def check_for_lava():
    """PROPER lava detection - checks actual block positions in front"""
    if not mining_active:
        return False
    
    # Get player position and orientation
    px, py, pz = m.player_position()
    yaw, pitch = m.player_orientation()
    
    # Get the direction the player is facing (for strip mining, usually one of the cardinal directions)
    # For strip mining, we're typically facing north/south/east/west
    facing_direction = get_facing_direction(yaw)
    
    # Check blocks in a 3x3 area in front of the player, up to 4 blocks away
    check_positions = []
    
    # Determine the mining direction based on player orientation
    if facing_direction == "north":  # -Z
        for distance in range(1, 5):  # Check 1 to 4 blocks away
            for dx in range(-1, 2):   # Check left, center, right
                check_positions.append((int(px + dx), int(py), int(pz - distance)))
                check_positions.append((int(px + dx), int(py + 1), int(pz - distance)))  # Check head level too
                
    elif facing_direction == "south":  # +Z
        for distance in range(1, 5):
            for dx in range(-1, 2):
                check_positions.append((int(px + dx), int(py), int(pz + distance)))
                check_positions.append((int(px + dx), int(py + 1), int(pz + distance)))
                
    elif facing_direction == "east":  # +X
        for distance in range(1, 5):
            for dz in range(-1, 2):
                check_positions.append((int(px + distance), int(py), int(pz + dz)))
                check_positions.append((int(px + distance), int(py + 1), int(pz + dz)))
                
    elif facing_direction == "west":  # -X
        for distance in range(1, 5):
            for dz in range(-1, 2):
                check_positions.append((int(px - distance), int(py), int(pz + dz)))
                check_positions.append((int(px - distance), int(py + 1), int(pz + dz)))
    
    # Remove duplicate positions
    check_positions = list(set(check_positions))
    
    # Check each position
    for check_x, check_y, check_z in check_positions:
        block_type = m.getblock(check_x, check_y, check_z)
        if block_type and ("lava" in block_type.lower() or "flowing_lava" in block_type.lower()):
            return True
    
    return False

def check_and_recover_from_fall(locked_yaw, locked_pitch):
    """Check if player fell and attempt to recover by jumping for 3 seconds"""
    global mining_active, original_y_level, fall_recovery_active
    
    if not mining_active or fall_recovery_active:
        return True  # Return True to continue if we're already in recovery
        
    current_y = m.player_position()[1]
    
    # If we haven't set the original Y level yet, set it now
    if original_y_level is None:
        original_y_level = current_y
        m.echo(f"📏 Original Y level set to: {original_y_level:.1f}")
        return True
    
    # Check if we fell more than 1 block
    y_difference = original_y_level - current_y
    if y_difference >= 1.0:
        m.echo(f"⚠️ Fall detected! Current Y: {current_y:.1f}, Original Y: {original_y_level:.1f} (difference: {y_difference:.1f}). Attempting recovery...")
        fall_recovery_active = True
        
        # CRITICAL: Stop ALL movement immediately
        m.player_press_forward(False)
        m.player_press_attack(False)
        m.player_press_backward(False)
        
        # Wait a moment to ensure movement stops
        time.sleep(0.2)
        
        # Look towards the original mining direction
        aim.player_aim.ultra_fast_rotate_to(locked_yaw, locked_pitch)
        time.sleep(0.1)
        
        # Attempt to jump for 3 seconds
        recovery_start_time = time.time()
        max_recovery_time = 3.0  # 3 seconds
        
        recovery_successful = False
        jump_count = 0
        
        m.echo("🔄 Starting jump recovery...")
        
        while mining_active and (time.time() - recovery_start_time) < max_recovery_time:
            if check_for_t_press():
                break
                
            # Press forward to try to move out of the hole
            m.player_press_forward(True)
            
            # Jump repeatedly
            m.player_press_jump(True)
            time.sleep(0.15)  # Hold jump for 0.15 seconds
            m.player_press_jump(False)
            time.sleep(0.1)   # Short pause between jumps
            
            # Check if we recovered
            current_y = m.player_position()[1]
            if current_y == original_y_level:
                recovery_successful = True
                m.echo("✅ Successfully recovered from fall! Continuing mining.")
                break
                
            jump_count += 1
            if jump_count % 3 == 0:  # Update every 3 jumps
                m.echo(f"🔄 Jump {jump_count}, Current Y: {current_y:.1f}, Target: {original_y_level:.1f}")
        
        # Stop all movement after recovery attempt
        m.player_press_forward(False)
        m.player_press_jump(False)
        fall_recovery_active = False
        
        if recovery_successful:
            time.sleep(0.2)
            m.player_press_forward(True)
            
            # Update original Y level to new position
            current_y = m.player_position()[1]
            original_y_level = current_y
            m.echo(f"📏 Updated Y level to: {original_y_level:.1f} - RESUMING FORWARD MOVEMENT")
            return True
        else:
            current_y = m.player_position()[1]
            m.echo(f"❌ Failed to recover from fall after 3 seconds. Current Y: {current_y:.1f}, Original: {original_y_level:.1f}. Stopping script.")
            stop_mining()
            return False
    
    return True

def monitor_fall_continuously(locked_yaw, locked_pitch):
    """Continuous fall monitoring that runs in parallel with mining - FIXED TypeError"""
    global mining_active, original_y_level, fall_recovery_active, last_y_check_time
    
    # Handle None values for locked_yaw/locked_pitch
    if locked_yaw is None or locked_pitch is None:
        return True
        
    current_time = time.time()
    if current_time - last_y_check_time < y_check_interval:
        return True
        
    last_y_check_time = current_time
    
    if not mining_active or fall_recovery_active:
        return True
        
    if original_y_level is None:
        return True
        
    current_y = m.player_position()[1]
    # FIXED: Ensure original_y_level is not None before subtraction
    if original_y_level is not None:
        y_difference = original_y_level - current_y
    else:
        return True
    
    # Trigger on any Y change >= 1 block
    if y_difference >= 1.0:
        m.echo(f"🔍 Fall monitor triggered: Y difference {y_difference:.1f}")
        # Force immediate recovery - don't return until recovery is complete
        recovery_result = check_and_recover_from_fall(locked_yaw, locked_pitch)
        return recovery_result
    
    return True

def get_facing_direction(yaw):
    """Convert yaw to cardinal direction for strip mining"""
    # Normalize yaw to 0-360
    normalized_yaw = yaw % 360
    if normalized_yaw < 0:
        normalized_yaw += 360
    
    # Determine cardinal direction
    if 315 <= normalized_yaw or normalized_yaw < 45:
        return "south"  # -Z in Minecraft, but we call it south for clarity
    elif 45 <= normalized_yaw < 135:
        return "west"   # -X
    elif 135 <= normalized_yaw < 225:
        return "north"  # +Z
    else:  # 225 <= normalized_yaw < 315
        return "east"   # +X

def lock_to_cardinal_direction():
    """Lock player to nearest cardinal direction with instant rotation - SINGLE PITCH VERSION"""
    if not mining_active:
        return None, None
    
    current_yaw, current_pitch = m.player_orientation()
    
    # Normalize yaw to 0-360
    normalized_yaw = current_yaw % 360
    if normalized_yaw < 0:
        normalized_yaw += 360
    
    # Lock to nearest cardinal direction
    if 315 <= normalized_yaw or normalized_yaw < 45:
        target_yaw = 0    # South
    elif 45 <= normalized_yaw < 135:
        target_yaw = 90   # West  
    elif 135 <= normalized_yaw < 225:
        target_yaw = 180  # North
    else:  # 225 <= normalized_yaw < 315
        target_yaw = 270  # East
    
    # Set pitch to 16 (your requested change)
    target_pitch = 16
    
    aim.player_aim.ultra_fast_rotate_to(target_yaw, target_pitch)
    return target_yaw, target_pitch

def emergency_lava_stop():
    """Emergency stop procedure when lava is detected - using ticks"""
    global mining_active
    
    m.echo("⚠️ LAVA DETECTED! EMERGENCY STOP!")
    
    m.player_press_forward(False)
    m.player_press_attack(False)

    m.player_press_backward(True)
    
    # Move backwards for 3 seconds (60 ticks)
    wait_ticks(60)
    
    m.player_press_backward(False)
    
    # Stop the script completely
    mining_active = False
    m.echo("Script stopped due to lava detection.")
    return True

def check_emergencies():
    """Check for emergency situations like lava"""
    if check_for_lava():
        return emergency_lava_stop()
    return False

def mine_at_angle(yaw, pitch, check_gravel=True):
    """Mine at specific angle using ultra-fast aiming"""
    if not mining_active:
        return False
        
    # Use hybrid rotation - instant for small moves, fast smooth for larger
    aim.player_aim.hybrid_rotate_to(yaw, pitch, fast_threshold=15.0)
    wait_ticks(1)  # Only 1 tick for aiming to settle

    # Check for gravel initially for both pitch angles
    if check_gravel and mining_active and pitch in [16]:
        # Initial gravel check
        if gravel_check(yaw, pitch):
            gravel_mine()
            return True
    
    if mining_active:
        # Get the targeted block position before mining
        targeted_block = m.player_get_targeted_block(max_distance=0.5)
        if not targeted_block or not targeted_block.position:
            # No block targeted, just do a quick mine
            m.player_press_attack(True)
            return False
            
        target_x, target_y, target_z = targeted_block.position
        original_block_type = m.getblock(target_x, target_y, target_z)
        
        # If it's air, no need to mine
        if not original_block_type or original_block_type == "minecraft:air":
            return False
        
        # Mine with ultra-fast block detection
        m.player_press_attack(True)
        
        start_ticks = 0
        max_mining_ticks = 30  # Reduced to 1.5 seconds max
        
        block_broken = False
        
        while mining_active and start_ticks < max_mining_ticks:
            if check_for_t_press():
                break
                
            # CONTINUOUS GRAVEL CHECK
            if check_gravel and pitch in [16]:
                current_targeted_block = m.player_get_targeted_block(max_distance=5)
                if current_targeted_block and current_targeted_block.type and "gravel" in current_targeted_block.type.lower():
                    m.player_press_attack(False)
                    wait_ticks(1)
                    gravel_mine()
                    return True
                
            # Check if block is broken
            current_block_type = m.getblock(target_x, target_y, target_z)
            if current_block_type == "minecraft:air":
                block_broken = True
                break
                
            wait_ticks(1)
            start_ticks += 1
        
        
        
    return False


def mine_single_block_simple(x, y, z):
    """Simple block mining for path clearing"""
    if not mining_active:
        return False
        
    # Check for T press
    if check_for_t_press():
        return False
        
    # Convert to integers
    x, y, z = int(x), int(y), int(z)
    
    # Calculate direction to block
    current_x, current_y, current_z = m.player_position()
    current_x, current_y, current_z = int(current_x), int(current_y), int(current_z)
    
    dx = x - current_x
    dy = y - current_y
    dz = z - current_z
    
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    if distance > 5:
        return False
        
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = 16
    
    # Look at the block
    m.player_set_orientation(yaw, pitch)
    time.sleep(0.3)
    
    # Mine the block
    m.player_press_attack(True)
    
    # Check for T press during mining
    start_time = time.time()
    while time.time() - start_time < 1.5 and mining_active:
        if check_for_t_press():
            m.player_press_attack(False)
            return False
        time.sleep(0.1)
        
    m.player_press_attack(False)
    time.sleep(0.2)
    
    # Check if block was mined
    return m.getblock(x, y, z) == "minecraft:air"

def is_ore_block(block_type):
    """Check if a block is an ore"""
    if not block_type:
        return False
    
    # Remove block states for comparison
    base_block_type = block_type.split('[')[0].split('{')[0].lower()
    
    ore_blocks = {
        
        "minecraft:ancient_debris", "minecraft:nether_gold_ore", "minecraft:nether_quartz_ore"
    }
    
    # Check for base ore types
    if base_block_type in ore_blocks:
        return True
    
    # Special case for lit redstone ore
    if "redstone_ore" in base_block_type:
        return True
    
    return False

def mine_ore_vein_continuous():
    """Continuously mine all visible ores in a vein - RETURNS TO CURRENT ORIENTATION"""
    global previous_target
    
    if not mining_active:
        return False

    # Save CURRENT orientation before ore mining
    current_orientation = m.player_orientation()
    
    ores_mined = 0
    max_ores_in_vein = 20
    
    while mining_active and ores_mined < max_ores_in_vein:
        px, py, pz = m.player_position()
        
        occluders = get_area(position=(px, py + 1.62, pz))

        # Filter out recently mined positions from occluders
        filtered_occluders = []
        for occluder in occluders:
            pos, base, simple, meta = occluder
            if pos not in recently_mined_positions:
                filtered_occluders.append(occluder)
        
        aim_result = scan_targets(
            position=(px, py + 1.62, pz), 
            target_ids=target_ids, 
            occluders=filtered_occluders, 
            previous_target=previous_target
        )

        if aim_result is None:
            break
            
        previous_target = aim_result.optimal_pos
        x, y, z = aim_result.world_pos
        
        # Skip if this position was recently mined
        if (x, y, z) in recently_mined_positions:
            continue
        
        if not is_player_close_to_ore(x, y, z):
            recently_mined_positions.add((x, y, z))
            continue
        
        # Aim at the ore
        aim.player_aim.hybrid_rotate_to(aim_result.target_angle[0], aim_result.target_angle[1], fast_threshold=15.0)
        time.sleep(0.5)
        
        # Get the ore type for logging
        ore_type = m.getblock(x, y, z)
        
        # Mine the ore completely
        m.player_press_attack(True)
        
        # Use time-based mining instead of block change detection
        mining_time = get_mining_time_for_ore(ore_type)
        
        start_time = time.time()
        ore_mined = False
        
        while mining_active and (time.time() - start_time) < mining_time:
            # Check for T press
            if check_for_t_press():
                break
                
            # Check if block is actually gone (air)
            current_block = m.getblock(x, y, z)
            if current_block == "minecraft:air":
                ore_mined = True
                break
                
            time.sleep(0.1)
        
        m.player_press_attack(False)
        
        if ore_mined:
            ores_mined += 1
            recently_mined_positions.add((x, y, z))
            
            # Small delay before looking for next ore
            time.sleep(0.5)
        else:
            m.echo(f"✗ FAILED: Could not mine {ore_type} completely")
            recently_mined_positions.add((x, y, z))
            break
    
    # After ore vein mining, return to CURRENT orientation and re-enable sneak
    if mining_active:
        m.player_set_orientation(current_orientation[0], current_orientation[1])
        time.sleep(0.1)
        m.player_press_forward(True)
    
    return ores_mined > 0


def is_player_close_to_ore(ore_x, ore_y, ore_z, max_distance=5):
    """Check if player is close enough to mine the ore directly"""
    player_x, player_y, player_z = m.player_position()
    distance = math.sqrt(
        (player_x - ore_x)**2 + 
        (player_y - ore_y)**2 + 
        (player_z - ore_z)**2
    )
    return distance <= max_distance

def get_mining_time_for_ore(ore_type):
    """Get appropriate mining time for different ore types"""
    if not ore_type:
        return 5.0
    
    ore_lower = ore_type.lower()
    
    if "ancient_debris" in ore_lower:
        return 15.0  # Very tough
    elif "diamond_ore" in ore_lower or "emerald_ore" in ore_lower:
        return 8.0   # Tough
    elif "redstone_ore" in ore_lower:
        return 6.0   # Medium-tough - needs extra time for state change
    elif "gold_ore" in ore_lower or "copper_ore" in ore_lower:
        return 5.0   # Medium
    elif "iron_ore" in ore_lower or "lapis_ore" in ore_lower:
        return 4.0   # Medium
    elif "coal_ore" in ore_lower:
        return 3.0   # Easy
    else:
        return 5.0   # Default



def perform_strip_mining():
    """Perform strip mining with dynamic basalt/blackstone detection"""
    global original_y_level
    
    if not mining_active:
        return False
    
    # Lock to cardinal direction with pitch 16
    lock_result = lock_to_cardinal_direction()
    if lock_result is None:
        return False
    locked_yaw, locked_pitch = lock_result
    
    # Set original Y level if not set
    if original_y_level is None:
        original_y_level = m.player_position()[1]
        m.echo(f"📏 Original Y level set to: {original_y_level:.1f}")
    
    # Check for basalt/blackstone at the start and handle dynamically
    if handle_basalt_blackstone_mining():
        # If we were in basalt/blackstone mode and exited, continue normal mining
        m.echo("🔄 Returning to normal mining mode...")
    
    if mining_active:
        m.player_press_forward(True)
    
    # Continuous mining loop
    movement_check_start = time.time()
    last_position = m.player_position()
    consecutive_stuck_checks = 0
    stuck_threshold = 3
    
    # Check interval for dynamic mode switching
    last_mode_check = time.time()
    mode_check_interval = 1.0  # Check for mode changes every second
    
    while mining_active:
        if check_for_t_press():
            break
        
        # Check for mode changes (normal <-> basalt/blackstone)
        current_time = time.time()
        if current_time - last_mode_check >= mode_check_interval:
            last_mode_check = current_time
            if handle_basalt_blackstone_mining():
                # If we entered and exited basalt/blackstone mode, reset stuck detection
                last_position = m.player_position()
                movement_check_start = time.time()
                consecutive_stuck_checks = 0
        
        # CONTINUOUS FALL DETECTION CHECK
        if not monitor_fall_continuously(locked_yaw, locked_pitch):
            last_position = m.player_position()
            movement_check_start = time.time()
            consecutive_stuck_checks = 0
            m.echo("🔄 Reset stuck detection after fall recovery")
            continue
        
        # LAVA CHECK
        if check_for_lava():
            m.echo("LAVA DETECTED! Stopping strip mining.")
            m.player_press_forward(False)
            emergency_lava_stop()
            return False
            
        # Mine at fixed pitch 16
        mine_at_angle(locked_yaw, 16, True)
        
        # CONTINUOUS MOVEMENT STUCK CHECK
        current_time = time.time()
        if current_time - movement_check_start >= 1.5:
            current_pos = m.player_position()
            distance_moved = math.sqrt(
                (current_pos[0] - last_position[0])**2 + 
                (current_pos[2] - last_position[2])**2
            )
            
            if distance_moved < 0.3:
                consecutive_stuck_checks += 1
                if distance_moved == 0.00:
                    break
                if consecutive_stuck_checks >= stuck_threshold:
                    break
            else:
                consecutive_stuck_checks = 0
            
            last_position = current_pos
            movement_check_start = current_time
            
        # Ore check
        if mining_active and ore_check():
            last_position = m.player_position()
            movement_check_start = time.time()
            consecutive_stuck_checks = 0
            continue
        
        wait_ticks(1)
    
    # IMPROVED STUCK HANDLING: Sneak and break block in front
    if mining_active and (consecutive_stuck_checks >= stuck_threshold or consecutive_stuck_checks > 0):
        m.echo("🚫 Stuck detected! Attempting to break blocking block...")
        m.player_press_forward(False)
        
        if mining_active:
            # Stop all movement first
            m.player_press_attack(False)
            m.player_press_forward(False)
            time.sleep(0.2)
            
            # Start sneaking to prevent falling if there's a gap
            m.player_press_sneak(True)
            time.sleep(0.3)  # Allow sneak to fully engage
            
            # Look directly at the block in front (pitch 16 for mining level)
            aim.player_aim.hybrid_rotate_to(locked_yaw, 16, fast_threshold=15.0)
            time.sleep(0.2)
            
            # Mine the blocking block aggressively
            m.player_press_attack(True)
            
            # Mine for longer to ensure the block breaks (some blocks take longer)
            stuck_mining_start = time.time()
            max_stuck_mining_time = 2.0  # 2 seconds max for stuck block
            
            while mining_active and (time.time() - stuck_mining_start) < max_stuck_mining_time:
                if check_for_t_press():
                    break
                
                # Check if we're still stuck by testing movement
                current_pos = m.player_position()
                if current_pos[0] != last_position[0] or current_pos[2] != last_position[2]:
                    m.echo("✅ Block broken! Resuming normal mining.")
                    break
                    
                time.sleep(0.1)
            
            # Stop mining and sneaking
            m.player_press_attack(False)
            m.player_press_sneak(False)
            time.sleep(0.2)
            
            # Try to move forward again
            m.player_press_forward(True)
            time.sleep(1.0)  # Give it a second to move
            
            # Check if we're still stuck after the attempt
            new_pos = m.player_position()
            still_stuck = (abs(new_pos[0] - last_position[0]) < 0.5 and 
                          abs(new_pos[2] - last_position[2]) < 0.5)
            
            if still_stuck:
                m.echo("❌ Still stuck after block break attempt. Trying alternative methods...")
                
                # Try moving backward then forward
                m.player_press_forward(False)
                m.player_press_backward(True)
                time.sleep(0.5)
                m.player_press_backward(False)
                m.player_press_forward(True)
                time.sleep(1.0)
                
                # Final check
                final_pos = m.player_position()
                if (abs(final_pos[0] - last_position[0]) < 0.5 and 
                    abs(final_pos[2] - last_position[2]) < 0.5):
                    m.echo("💥 Completely stuck! Stopping mining.")
                    stop_mining()
                    return False
            
            # Reset stuck detection for next cycle
            last_position = m.player_position()
            movement_check_start = time.time()
            consecutive_stuck_checks = 0
            
            if check_for_t_press():
                m.player_press_forward(False)
                return False
                
            if check_for_lava():
                m.echo("LAVA DETECTED! Stopping strip mining.")
                m.player_press_forward(False)
                emergency_lava_stop()
                return False
    
    if mining_active:
        m.player_press_forward(False)
    
    return False


def quick_ore_scan():
    """Quick scan for ores using ultra-fast aiming"""
    global previous_target
    
    if not mining_active:
        return False

    # Save CURRENT orientation before ore mining
    current_orientation = m.player_orientation()
    
    ores_mined = 0
    max_quick_ores = 15
    
    temp_mined_positions = set()
    
    while mining_active and ores_mined < max_quick_ores:
        px, py, pz = m.player_position()
        
        occluders = get_area(position=(px, py + 1.62, pz))

        filtered_occluders = []
        for occluder in occluders:
            pos, base, simple, meta = occluder
            if pos not in recently_mined_positions and pos not in temp_mined_positions:
                filtered_occluders.append(occluder)
        
        aim_result = scan_targets(
            position=(px, py + 1.62, pz), 
            target_ids=target_ids, 
            occluders=filtered_occluders, 
            previous_target=previous_target
        )

        if aim_result is None:
            break
            
        previous_target = aim_result.optimal_pos
        x, y, z = aim_result.world_pos
        
        # STOP MOVEMENT before ore mining
        m.player_press_forward(False)
        
        
        aim.player_aim.hybrid_rotate_to(aim_result.target_angle[0], aim_result.target_angle[1], fast_threshold=15.0)
        wait_ticks(1)  # Only 1 tick
        
        ore_type = m.getblock(x, y, z)
        
        # Mine using targeting system
        m.player_press_attack(True)
        
        start_ticks = 0
        max_mining_ticks = int(get_mining_time_for_ore(ore_type) * 20 * 0.5)  # 50% faster mining
        
        ore_mined = False
        
        while mining_active and start_ticks < max_mining_ticks:
            if check_for_t_press():
                break
            current_block = m.getblock(x, y, z)
            if current_block == "minecraft:air":
                ore_mined = True
                break
            wait_ticks(1)
            start_ticks += 1
            
        m.player_press_attack(False)
        
        if ore_mined:
            ores_mined += 1
            temp_mined_positions.add((x, y, z))
            recently_mined_positions.add((x, y, z))
            wait_ticks(3)  # Reduced from 6 ticks
        else:
            temp_mined_positions.add((x, y, z))
            recently_mined_positions.add((x, y, z))
            break
    
    # After ore mining, return to CURRENT orientation
    if ores_mined > 0 and mining_active:
        aim.player_aim.hybrid_rotate_to(current_orientation[0], current_orientation[1], fast_threshold=15.0)
        wait_ticks(1)
        m.player_press_forward(True)
        return True
    
    return False

def ore_check():
    """ULTRA-FAST ore check using targeting system"""
    global previous_target
    
    if not mining_active:
        return False

    px, py, pz = m.player_position()
    
    occluders = get_area(position=(px, py + 1.62, pz))

    filtered_occluders = []
    for occluder in occluders:
        pos, base, simple, meta = occluder
        if pos not in recently_mined_positions:
            filtered_occluders.append(occluder)
    
    aim_result = scan_targets(
        position=(px, py + 1.62, pz), 
        target_ids=target_ids, 
        occluders=filtered_occluders, 
        previous_target=previous_target
    )

    if aim_result is None:
        return False
        
    return quick_ore_scan()


def mining_time():
    """Main mining loop using tick-based timing"""
    global mining_active, previous_target, recently_mined_positions, original_y_level, fall_recovery_active, last_y_check_time
    
    mining_active = True
    previous_target = m.player_position()
    recently_mined_positions.clear()
    original_y_level = None
    fall_recovery_active = False
    last_y_check_time = time.time()
    
    # Lock to cardinal direction at start
    lock_to_cardinal_direction()
    
    # Convert time intervals to tick intervals
    ore_check_interval_ticks = 30
    chat_check_interval_ticks = 3
    lava_check_interval_ticks = 6
    
    last_ore_check_ticks = 0
    last_chat_check_ticks = 0
    last_lava_check_ticks = 0
    current_tick = 0
    
    
    m.echo("Press T to stop. Fall detection active.")
    
    try:
        while mining_active:
            current_tick += 1
            
            # Check for T press
            if current_tick - last_chat_check_ticks >= chat_check_interval_ticks:
                if check_for_t_press():
                    break
                last_chat_check_ticks = current_tick
            
            # Lava detection
            if current_tick - last_lava_check_ticks >= lava_check_interval_ticks:
                if check_for_lava():
                    m.echo("MAIN LOOP: Lava detected - emergency stop!")
                    emergency_lava_stop()
                    break
                last_lava_check_ticks = current_tick
            
            # Use targeting-based strip mining
            ore_mined_in_cycle = perform_strip_mining()
            
            if ore_mined_in_cycle:
                last_ore_check_ticks = current_tick + 30
                continue
            
            # Less frequent full ore vein scans
            if current_tick - last_ore_check_ticks >= ore_check_interval_ticks:
                if len(recently_mined_positions) > 30:
                    recently_mined_positions = set(list(recently_mined_positions)[-15:])
                
                if random.random() < 0.4:
                    vein_mined = mine_ore_vein_continuous()
                    if vein_mined:
                        last_ore_check_ticks = current_tick + 40
                    else:
                        last_ore_check_ticks = current_tick
                else:
                    last_ore_check_ticks = current_tick + 10
            
            # Small tick delay to prevent CPU overload
            wait_ticks(1)
            
    finally:
        m.player_press_forward(False)
        m.player_press_attack(False)
        m.player_press_backward(False)
        m.player_press_jump(False)  # Ensure jump is released
        m.echo("Mining script stopped completely.")

# Start the mining script immediately
mining_time()