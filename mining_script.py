from visibility_scanner.scanner import scan_targets, scan_target
from visibility_scanner.world_scanners import get_area, get_line
import aim.player_aim

import threading
import time
import math

import minescript as m


# ------------------------------
# params
# ------------------------------

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


# ------------------------------
# gravel detection and handling (from mining_script.py)
# ------------------------------

def check_gravel_block(yaw, pitch=20):
    """Check if the targeted block at given orientation is gravel"""
    if not mining_active:
        return False
        
    # Set orientation to check for gravel
    m.player_set_orientation(yaw, pitch)
    time.sleep(0.1)
    
    targeted_block = m.player_get_targeted_block(max_distance=5)
    
    if targeted_block and targeted_block.type:
        return "gravel" in targeted_block.type.lower()
    return False

def gravel_mine():
    """Handle gravel mining with torch placement"""
    if not mining_active:
        return
        
    yaw, pitch = m.player_orientation()
    
    # Switch to torch (assuming hotbar slot 9 has torch)
    m.press_key_bind("key.hotbar.9", True)
    time.sleep(0.2)
    m.press_key_bind("key.hotbar.9", False)
    
    # Mine the gravel
    m.player_press_attack(True)
    for _ in range(20):
        if not mining_active:
            m.player_press_attack(False)
            return
        time.sleep(0.1)
    m.player_press_attack(False)
    
    # Switch back to pickaxe (assuming hotbar slot 1)
    if mining_active:
        m.press_key_bind("key.hotbar.1", True)
        time.sleep(0.2)
        m.press_key_bind("key.hotbar.1", False)

def mine_at_angle(yaw, pitch, check_gravel=True):
    """Mine at specific angle, with optional gravel check"""
    if not mining_active:
        return False
        
    m.player_set_orientation(yaw, pitch)

    if check_gravel and pitch == 20 and mining_active:
        if check_gravel_block(yaw, pitch):
            gravel_mine()
            return True
    
    if mining_active:
        m.player_press_attack(True)
        for _ in range(5):
            if not mining_active:
                m.player_press_attack(False)
                return False
            time.sleep(0.1)
        m.player_press_attack(False)
    return False


# ------------------------------
# path clearing (from mining_script.py)
# ------------------------------

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

def clear_path_to_ore(ore_x, ore_y, ore_z):
    """Clear blocks between player and ore - IMPROVED VERSION"""
    if not mining_active:
        return False
        
    # Check for T press
    if check_for_t_press():
        return False
        
    # Convert ore coordinates to integers
    ore_x, ore_y, ore_z = int(ore_x), int(ore_y), int(ore_z)
    
    player_x, player_y, player_z = m.player_position()
    player_x, player_y, player_z = int(player_x), int(player_y), int(player_z)
    
    m.echo(f"Clearing path to ore at {ore_x}, {ore_y}, {ore_z}")
    
    # RELEASE SNEAK when clearing path
    m.player_press_sneak(False)
    m.echo("Released sneak for path clearing")
    
    # Calculate direction and distance
    dx = ore_x - player_x
    dy = ore_y - player_y  
    dz = ore_z - player_z
    
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    if distance > 6:
        m.echo(f"Ore too far: {distance:.1f} blocks")
        return False
    
    blocks_cleared = 0
    
    # Improved path clearing - only clear blocks that are actually in the way
    # Use Bresenham's line algorithm for better path finding
    steps = max(int(distance * 2), 5)  # More samples for better accuracy
    
    for i in range(1, steps):
        if not mining_active:
            break
            
        # Check for T press
        if check_for_t_press():
            break
            
        # Calculate position along the path with interpolation
        progress = i / (steps - 1)
        check_x = player_x + int(dx * progress)
        check_y = player_y + int(dy * progress)
        check_z = player_z + int(dz * progress)
        
        # Stop if we reach or pass the ore
        if (abs(check_x - ore_x) <= 1 and abs(check_y - ore_y) <= 1 and abs(check_z - ore_z) <= 1):
            break
            
        block_type = m.getblock(check_x, check_y, check_z)
        
        # If it's a solid block (not air, not ore), mine it
        if (block_type and 
            block_type != "minecraft:air" and 
            not is_ore_block(block_type) and
            "liquid" not in block_type.lower() and
            "bedrock" not in block_type.lower()):
            
            m.echo(f"Clearing path block: {block_type} at {check_x}, {check_y}, {check_z}")
            
            # Use simple mining for path blocks
            if mine_single_block_simple(check_x, check_y, check_z):
                blocks_cleared += 1
                # Small delay after clearing a block
                time.sleep(0.2)
    
    m.echo(f"Path clearing complete. Cleared {blocks_cleared} blocks.")
    return blocks_cleared > 0

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


# ------------------------------
# strip mining cycle (from mining_script.py)
# ------------------------------

def perform_strip_mining_cycle():
    """Perform one complete strip mining cycle with gravel detection"""
    if not mining_active:
        return False
        
    # REGULAR MINING MODE - Press sneak for safety
    if mining_active:
        yaw, pitch = m.player_orientation()
        m.player_press_sneak(True)
    
    if mining_active:
        m.player_press_forward(True)
    
    mining_steps = [
        (yaw, 0, False), (yaw, 20, True), (yaw, 0, False), (yaw, 20, True)
    ]
    
    for step_yaw, step_pitch, check_gravel in mining_steps:
        if not mining_active:
            break
        if check_for_t_press():
            break
        mine_at_angle(step_yaw, step_pitch, check_gravel)
    
    if mining_active:
        m.player_press_forward(False)
    
    if mining_active:
        mining_steps_2 = [(yaw, 0, False), (yaw, 20, True)]
        for step_yaw, step_pitch, check_gravel in mining_steps_2:
            if not mining_active:
                break
            if check_for_t_press():
                break
            mine_at_angle(step_yaw, step_pitch, check_gravel)
    
    if mining_active:
        yaw, pitch = m.player_orientation()
    
    if mining_active:
        m.player_press_forward(True)
    
    if mining_active:
        mining_steps_3 = [(yaw, 0, False), (yaw, 20, True), (yaw, 0, False), (yaw, 20, True)]
        for step_yaw, step_pitch, check_gravel in mining_steps_3:
            if not mining_active:
                break
            if check_for_t_press():
                break
            mine_at_angle(step_yaw, step_pitch, check_gravel)
    
    if mining_active:
        m.player_press_forward(False)
    
    if mining_active:
        mining_steps_4 = [(yaw, 0, False), (yaw, 20, True)]
        for step_yaw, step_pitch, check_gravel in mining_steps_4:
            if not mining_active:
                break
            if check_for_t_press():
                break
            mine_at_angle(step_yaw, step_pitch, check_gravel)
    
    if mining_active:
        m.player_press_forward(True)
        for i in range(3): 
            if not mining_active:
                m.player_press_forward(False)
                break
            if check_for_t_press():
                m.player_press_forward(False)
                break
            time.sleep(0.1)
        if mining_active:
            m.player_press_forward(False)
    
    if mining_active:
        m.echo("Mining cycle complete")
        
    return True


# ------------------------------
# CONTINUOUS ORE VEIN MINING
# ------------------------------

def mine_ore_vein_continuous():
    """Continuously mine all visible ores in a vein before returning to strip mining"""
    global previous_target
    
    if not mining_active:
        return False

    # Save original position and orientation before ore mining
    original_position = m.player_position()
    original_orientation = m.player_orientation()
    
    m.echo("Starting continuous ore vein mining...")
    
    ores_mined = 0
    max_ores_in_vein = 20  # Maximum ores to mine in one vein to prevent going too far
    
    while mining_active and ores_mined < max_ores_in_vein:
        px, py, pz = m.player_position()
        
        m.echo("Scanning for nearby ores...")
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
            m.echo("No more visible ores found in this vein.")
            break
            
        previous_target = aim_result.optimal_pos
        x, y, z = aim_result.world_pos
        
        # Skip if this position was recently mined
        if (x, y, z) in recently_mined_positions:
            m.echo(f"Skipping recently mined ore at {x}, {y}, {z}")
            continue
        
        # Clear path to ore first
        m.echo(f"Found ore at {x}, {y}, {z}. Clearing path...")
        path_cleared = clear_path_to_ore(x, y, z)
        
        if not path_cleared and not is_player_close_to_ore(x, y, z):
            m.echo(f"Could not clear path to ore at {x}, {y}, {z}. Skipping.")
            recently_mined_positions.add((x, y, z))
            continue
        
        # RELEASE SNEAK for ore mining
        m.player_press_sneak(False)
        m.echo("Released sneak for ore mining")
        
        # Aim at the ore
        aim.player_aim.smooth_rotate_to(aim_result.target_angle[0], aim_result.target_angle[1], duration=0.3)
        time.sleep(0.5)
        
        # Get the ore type for logging
        ore_type = m.getblock(x, y, z)
        m.echo(f"Ore type: {ore_type}")
        
        # Mine the ore completely
        m.player_press_attack(True)
        
        # Use time-based mining instead of block change detection
        mining_time = get_mining_time_for_ore(ore_type)
        m.echo(f"Mining for {mining_time} seconds...")
        
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
            m.echo(f"✓ SUCCESS: Mined {ore_type}!")
            ores_mined += 1
            recently_mined_positions.add((x, y, z))
            m.echo(f"Ores mined in this vein: {ores_mined}")
            
            # Small delay before looking for next ore
            time.sleep(0.5)
        else:
            m.echo(f"✗ FAILED: Could not mine {ore_type} completely")
            recently_mined_positions.add((x, y, z))
            break
    
    # ALWAYS restore original orientation and position after ore vein mining
    if mining_active:
        m.echo(f"Ore vein mining complete. Mined {ores_mined} ores.")
        m.echo("Restoring original position and orientation...")
        return_to_position(original_position, original_orientation)
    
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
    
    # If we're close enough, just set orientation
    if distance < 2:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.5)
        m.echo(f"Restored orientation: {target_orientation}")
        return
    
    # Otherwise, look toward target and move
    dx = target_x - current_x
    dz = target_z - current_z
    yaw = math.degrees(math.atan2(-dx, dz))
    
    m.player_set_orientation(yaw, 0)
    time.sleep(0.5)
    
    # Move toward target
    m.player_press_forward(True)
    
    while mining_active and distance > 1:
        # Check for T press
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
        
        if distance <= 1:
            break
            
        time.sleep(0.1)
    
    m.player_press_forward(False)
    
    # Set final orientation
    if mining_active:
        m.player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.5)
        m.echo(f"Restored orientation: {target_orientation}")


def mining_time():
    """Main mining loop that combines strip mining with ore detection"""
    global mining_active, previous_target, recently_mined_positions
    
    mining_active = True
    previous_target = m.player_position()
    recently_mined_positions.clear()
    last_ore_check = time.time()
    ore_check_interval = 2.0  # Check for ores every 2 seconds
    last_chat_check = time.time()
    
    m.echo("Integrated mining script started!")
    m.echo("Press T to stop. Will perform strip mining and automatically detect/mine ore veins.")
    
    try:
        while mining_active:
            current_time = time.time()
            
            # Check for T press more frequently
            if current_time - last_chat_check > 0.1:
                if check_for_t_press():
                    break
                last_chat_check = current_time
            
            # Check for ores periodically
            if current_time - last_ore_check > ore_check_interval:
                vein_mined = mine_ore_vein_continuous()
                if vein_mined:
                    # If we mined a vein, wait a bit before continuing strip mining
                    last_ore_check = time.time() + 5.0
                    continue
                last_ore_check = current_time
            
            # Perform regular strip mining cycle
            perform_strip_mining_cycle()
            
    finally:
        # Always release all keys when stopping
        m.player_press_sneak(False)
        m.player_press_forward(False)
        m.player_press_attack(False)
        m.echo("Mining script stopped completely.")

# Start the mining script immediately
m.echo("Starting integrated mining script...")
m.echo("Strip mining with continuous ore vein detection active.")
m.echo("Press T to stop the script.")

mining_time()