from visibility_scanner.scanner import scan_targets, scan_target
from visibility_scanner.world_scanners import get_area, get_line
import aim.player_aim

import threading
import time
import math
import random

import minescript as m


target_ids = [
    "minecraft:diamond_ore",
    "minecraft:deepslate_diamond_ore",
    "minecraft:coal_ore",
    "minecraft:deepslate_coal_ore",
    "minecraft:iron_ore", 
    "minecraft:deepslate_iron_ore",
    "minecraft:gold_ore",
    "minecraft:deepslate_gold_ore",
    "minecraft:emerald_ore",
    "minecraft:deepslate_emerald_ore",
    "minecraft:lapis_ore",
    "minecraft:deepslate_lapis_ore",
    "minecraft:redstone_ore",
    "minecraft:deepslate_redstone_ore",
    "minecraft:copper_ore",
    "minecraft:deepslate_copper_ore",
    "minecraft:ancient_debris"
]

reach = 4.8
previous_target = m.player_position()

# Global flag to control the mining loop
mining_active = True
recently_mined_positions = set()  # Track recently mined positions to avoid repeats

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
        m.echo("T pressed! Stopping mining script.")
        stop_mining()
        return True
    return False


def gravel_check(yaw, pitch):
    """Fast gravel check for both pitch angles (0 and 20)"""
    if not mining_active:
        return False
        
    # Set orientation to ensure we're looking at the right spot
    m.player_set_orientation(yaw, pitch)
    wait_ticks(1)  # 1 tick for orientation to settle
    
    targeted_block = m.player_get_targeted_block(max_distance=5)
    
    if targeted_block and targeted_block.type:
        is_gravel = "gravel" in targeted_block.type.lower()
        if is_gravel:
            m.echo(f"Gravel detected at pitch {pitch}! Switching to shovel.")
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

def emergency_lava_stop():
    """Emergency stop procedure when lava is detected - using ticks"""
    global mining_active
    
    m.echo("⚠️ LAVA DETECTED! EMERGENCY STOP!")
    
    # Release all keys immediately
    m.player_press_sneak(False)
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
    """Mine at specific angle using targeting system to detect when block breaks"""
    if not mining_active:
        return False
        
    m.player_set_orientation(yaw, pitch)

    # Check for gravel initially for both pitch angles
    if check_gravel and mining_active and pitch in [0, 20]:
        # Initial gravel check
        if gravel_check(yaw, pitch):
            gravel_mine()
            return True
    
    if mining_active:
        # Get the targeted block position before mining
        targeted_block = m.player_get_targeted_block(max_distance=5)
        if not targeted_block or not targeted_block.position:
            # No block targeted, just do a quick mine
            m.player_press_attack(True)
            wait_ticks(4)  # 4 ticks = 0.2 seconds
            m.player_press_attack(False)
            return False
            
        target_x, target_y, target_z = targeted_block.position
        original_block_type = m.getblock(target_x, target_y, target_z)
        
        # If it's air, no need to mine
        if not original_block_type or original_block_type == "minecraft:air":
            return False
        
        # Mine until the block breaks, with continuous gravel checking for both pitches
        m.player_press_attack(True)
        
        start_ticks = 0
        max_mining_ticks = 60  # Maximum 3 seconds in ticks (60 ticks)
        
        while mining_active and start_ticks < max_mining_ticks:
            if check_for_t_press():
                break
                
            # CONTINUOUS GRAVEL CHECK - if targeted block changes to gravel for either pitch
            if check_gravel and pitch in [0, 20]:
                current_targeted_block = m.player_get_targeted_block(max_distance=5)
                if current_targeted_block and current_targeted_block.type and "gravel" in current_targeted_block.type.lower():
                    m.player_press_attack(False)  # Stop current mining
                    wait_ticks(1)  # 1 tick pause
                    gravel_mine()  # Use shovel for gravel
                    return True
                
            # Check if the block is now air (broken)
            current_block_type = m.getblock(target_x, target_y, target_z)
            if current_block_type == "minecraft:air":
                break
                
            wait_ticks(1)  # Wait 1 tick between checks
            start_ticks += 1
        
        m.player_press_attack(False)
        
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
    pitch = math.degrees(math.asin(-dy / distance)) if distance > 0 else 0
    
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
        "minecraft:coal_ore", "minecraft:deepslate_coal_ore",
        "minecraft:iron_ore", "minecraft:deepslate_iron_ore", 
        "minecraft:gold_ore", "minecraft:deepslate_gold_ore",
        "minecraft:diamond_ore", "minecraft:deepslate_diamond_ore",
        "minecraft:emerald_ore", "minecraft:deepslate_emerald_ore",
        "minecraft:lapis_ore", "minecraft:deepslate_lapis_ore",
        "minecraft:redstone_ore", "minecraft:deepslate_redstone_ore",
        "minecraft:copper_ore", "minecraft:deepslate_copper_ore",
        "minecraft:ancient_debris", "minecraft:nether_gold_ore"
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
        
        # RELEASE SNEAK for ore mining
        m.player_press_sneak(False)
        
        # Aim at the ore
        aim.player_aim.smooth_rotate_to(aim_result.target_angle[0], aim_result.target_angle[1], duration=0.3)
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
        m.player_press_sneak(True)
        time.sleep(0.1)
    
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

def return_to_position(target_position, target_orientation):
    """Return to the original position and orientation"""
    if not mining_active:
        return
        
    # Check for T press
    if check_for_t_press():
        return
        
    current_pos = m.player_position()
    current_ori = m.player_orientation()
    
    target_x, target_y, target_z = target_position
    current_x, current_y, current_z = current_pos
    
    # Calculate distance to target
    distance = math.sqrt(
        (target_x - current_x)**2 + 
        (target_y - current_y)**2 + 
        (target_z - current_z)**2
    )
    
    # If we're close enough (within 1 block), just set orientation and return
    # This prevents unnecessary backward movement
    if distance < 1.5:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.3)
        return
    
    # Only move back if we're significantly ahead of the target position
    # Check if we're mostly in front of the target (in the mining direction)
    dx = current_x - target_x
    dz = current_z - target_z
    
    # Get the mining direction from the target orientation
    mining_yaw = target_orientation[0]
    mining_dir_x = -math.sin(math.radians(mining_yaw))
    mining_dir_z = math.cos(math.radians(mining_yaw))
    
    # Calculate how far we are in the mining direction
    dot_product = dx * mining_dir_x + dz * mining_dir_z
    
    if dot_product > 0.5:  
        # Just reorient and continue from current position
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.3)
        return
    
    # Otherwise, look toward target and move (only if really needed)
    yaw = math.degrees(math.atan2(-dx, dz))
    
    m.player_set_orientation(yaw, 0)
    time.sleep(0.3)
    
    # Move toward target but only for a short time
    m.player_press_forward(True)
    
    start_time = time.time()
    while mining_active and distance > 1.0 and (time.time() - start_time) < 2.0:  # Max 2 seconds
        if check_for_t_press():
            m.player_press_forward(False)
            return
            
        current_pos = m.player_position()
        current_x, current_y, current_z = current_pos
        
        distance = math.sqrt(
            (target_x - current_x)**2 + 
            (target_y - current_y)**2 + 
            (target_z - current_z)**2
        )
        
        if distance <= 1.0:
            break
            
        time.sleep(0.1)
    
    m.player_press_forward(False)
    
    # Set final orientation
    if mining_active:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.3)


def perform_strip_mining():
    """Perform strip mining using targeting system for faster block detection"""
    if not mining_active:
        return False
        
    if mining_active:
        yaw, pitch = m.player_orientation()
        m.player_press_sneak(True)
        wait_ticks(1)  # 1 tick
    
    if mining_active:
        m.player_press_forward(True)
    
    # First set of mining steps with targeting (4 steps) - enable gravel check for both pitches
    mining_steps = [
        (yaw, 0, True), (yaw, 20, True), (yaw, 0, True), (yaw, 20, True)  # All check for gravel now
    ]
    
    for step_yaw, step_pitch, check_gravel in mining_steps:
        if not mining_active:
            break
        if check_for_t_press():
            break
        
        # LAVA CHECK
        if check_for_lava():
            m.echo("LAVA DETECTED! Stopping strip mining.")
            m.player_press_forward(False)
            emergency_lava_stop()
            return False
            
        # Use targeting-based mining with gravel checking for both pitches
        mine_at_angle(step_yaw, step_pitch, check_gravel)
        
        # QUICK ore scan
        if mining_active and ore_check():
            m.player_press_forward(False)
            # No need to return to position - ore_check already handles orientation
            return True
    
    if mining_active:
        m.player_press_forward(False)
    
    # Second set of mining steps with targeting (2 steps) - enable gravel check for both pitches
    if mining_active:
        mining_steps_2 = [(yaw, 0, True), (yaw, 20, True)]  # Both check for gravel
        for step_yaw, step_pitch, check_gravel in mining_steps_2:
            if not mining_active:
                break
            if check_for_t_press():
                break
            
            # LAVA CHECK
            if check_for_lava():
                m.echo("LAVA DETECTED! Stopping strip mining.")
                m.player_press_forward(False)
                emergency_lava_stop()
                return False
                
            mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            if mining_active and ore_check():
                m.player_press_forward(False)
                return True
    
    if mining_active:
        yaw, pitch = m.player_orientation()
    
    if mining_active:
        m.player_press_forward(True)
    
    # Third set of mining steps with targeting (4 steps) - enable gravel check for both pitches
    if mining_active:
        mining_steps_3 = [(yaw, 0, True), (yaw, 20, True), (yaw, 0, True), (yaw, 20, True)]  # All check for gravel
        for step_yaw, step_pitch, check_gravel in mining_steps_3:
            if not mining_active:
                break
            if check_for_t_press():
                break
            
            # LAVA CHECK
            if check_for_lava():
                m.echo("LAVA DETECTED! Stopping strip mining.")
                m.player_press_forward(False)
                emergency_lava_stop()
                return False
                
            mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            if mining_active and ore_check():
                m.player_press_forward(False)
                return True
    
    if mining_active:
        m.player_press_forward(False)
    
    # Fourth set of mining steps with targeting (2 steps) - enable gravel check for both pitches
    if mining_active:
        mining_steps_4 = [(yaw, 0, True), (yaw, 20, True)]  # Both check for gravel
        for step_yaw, step_pitch, check_gravel in mining_steps_4:
            if not mining_active:
                break
            if check_for_t_press():
                break
            
            # LAVA CHECK
            if check_for_lava():
                m.echo("LAVA DETECTED! Stopping strip mining.")
                m.player_press_forward(False)
                emergency_lava_stop()
                return False
                
            mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            if mining_active and ore_check():
                m.player_press_forward(False)
                return True
    
    # Final forward movement (3 steps)
    if mining_active:
        m.player_press_forward(True)
        for i in range(3): 
            if not mining_active:
                m.player_press_forward(False)
                break
            if check_for_t_press():
                m.player_press_forward(False)
                break
            
            # LAVA CHECK
            if check_for_lava():
                m.echo("LAVA DETECTED! Stopping strip mining.")
                m.player_press_forward(False)
                emergency_lava_stop()
                return False
                
            wait_ticks(1)  # 1 tick per forward step
        if mining_active:
            m.player_press_forward(False)
    
    return False


def quick_ore_scan():
    """Quick scan for ores using targeting system - RETURNS TO CURRENT ORIENTATION"""
    global previous_target
    
    if not mining_active:
        return False

    # Save CURRENT orientation before ore mining
    current_orientation = m.player_orientation()
    
    ores_mined = 0
    max_quick_ores = 5
    
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
        m.player_press_sneak(False)
        wait_ticks(1)  # 1 tick
        
        # Quick aim and mine
        aim.player_aim.smooth_rotate_to(aim_result.target_angle[0], aim_result.target_angle[1], duration=0.15)
        wait_ticks(4)  # 4 ticks = 0.2 seconds
        
        ore_type = m.getblock(x, y, z)
        
        # Mine using targeting system
        m.player_press_attack(True)
        
        start_ticks = 0
        max_mining_ticks = int(get_mining_time_for_ore(ore_type) * 20 * 0.7)  # Convert to ticks
        
        ore_mined = False
        
        while mining_active and start_ticks < max_mining_ticks:
            if check_for_t_press():
                break
            current_block = m.getblock(x, y, z)
            if current_block == "minecraft:air":
                ore_mined = True
                break
            wait_ticks(1)  # Check every tick
            start_ticks += 1
            
        m.player_press_attack(False)
        
        if ore_mined:
            ores_mined += 1
            temp_mined_positions.add((x, y, z))
            recently_mined_positions.add((x, y, z))
            wait_ticks(6)  # 6 ticks = 0.3 seconds
        else:
            temp_mined_positions.add((x, y, z))
            recently_mined_positions.add((x, y, z))
            break
    
    # After ore mining, return to CURRENT orientation and re-enable sneak
    if ores_mined > 0 and mining_active:
        m.player_set_orientation(current_orientation[0], current_orientation[1])
        wait_ticks(2)  # 2 ticks = 0.1 seconds
        m.player_press_sneak(True)
        wait_ticks(2)  # 2 ticks = 0.1 seconds
        return True
    
    return False

def return_to_position(target_position, target_orientation):
    """Return to the original position and orientation - OPTIMIZED"""
    if not mining_active:
        return
        
    # Check for T press
    if check_for_t_press():
        return
        
    current_pos = m.player_position()
    
    target_x, target_y, target_z = target_position
    current_x, current_y, current_z = current_pos
    
    # Calculate distance to target
    distance = math.sqrt(
        (target_x - current_x)**2 + 
        (target_y - current_y)**2 + 
        (target_z - current_z)**2
    )
    
    # If we're close enough (within 1 block), just set orientation and return
    if distance < 1.5:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.1)  # Reduced
        return
    
    # Otherwise, look toward target and move quickly
    dx = current_x - target_x
    dz = current_z - target_z
    yaw = math.degrees(math.atan2(-dx, dz))
    
    m.player_set_orientation(yaw, 0)
    time.sleep(0.1)  # Reduced
    
    # Move toward target but only for a short time
    m.player_press_forward(True)
    
    start_time = time.time()
    while mining_active and distance > 1.0 and (time.time() - start_time) < 1.0:  # Max 1 second
        if check_for_t_press():
            m.player_press_forward(False)
            return
            
        current_pos = m.player_position()
        current_x, current_y, current_z = current_pos
        
        distance = math.sqrt(
            (target_x - current_x)**2 + 
            (target_y - current_y)**2 + 
            (target_z - current_z)**2
        )
        
        if distance <= 1.0:
            break
            
        time.sleep(0.05)  # Reduced
    
    m.player_press_forward(False)
    
    # Set final orientation
    if mining_active:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.1)  # Reduced

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
    global mining_active, previous_target, recently_mined_positions
    
    mining_active = True
    previous_target = m.player_position()
    recently_mined_positions.clear()
    
    # Convert time intervals to tick intervals
    ore_check_interval_ticks = 30  # 1.5 seconds in ticks
    chat_check_interval_ticks = 3  # 0.15 seconds in ticks
    lava_check_interval_ticks = 6  # 0.3 seconds in ticks
    
    last_ore_check_ticks = 0
    last_chat_check_ticks = 0
    last_lava_check_ticks = 0
    current_tick = 0
    
    m.player_press_sneak(True)
    wait_ticks(2)  # 2 ticks = 0.1 seconds
    
    m.echo("Press T to stop. TICK-BASED strip mining active.")
    
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
                last_ore_check_ticks = current_tick + 30  # Wait 1.5 seconds (30 ticks)
                continue
            
            # Less frequent full ore vein scans
            if current_tick - last_ore_check_ticks >= ore_check_interval_ticks:
                if len(recently_mined_positions) > 30:
                    recently_mined_positions = set(list(recently_mined_positions)[-15:])
                
                if random.random() < 0.4:
                    vein_mined = mine_ore_vein_continuous()
                    if vein_mined:
                        last_ore_check_ticks = current_tick + 40  # Wait 2 seconds (40 ticks)
                    else:
                        last_ore_check_ticks = current_tick
                else:
                    last_ore_check_ticks = current_tick + 10  # Wait 0.5 seconds (10 ticks)
            
            # Small tick delay to prevent CPU overload
            wait_ticks(1)
            
    finally:
        m.player_press_sneak(False)
        m.player_press_forward(False)
        m.player_press_attack(False)
        m.player_press_backward(False)
        m.echo("Mining script stopped completely.")

# Start the mining script immediately
m.echo("Strip mining with real-time block detection active.")
mining_time()