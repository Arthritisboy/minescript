from minescript import *
import time
import math

# Global flag to control the mining loop
mining_active = True

def stop_mining():
    global mining_active
    mining_active = False

def get_ore_blocks_around(position, radius=3):
    """Scan for ore blocks around the given position"""
    ore_blocks = []
    x, y, z = position
    
    # Scan in a cube around the position
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                # Skip the center block and blocks too far
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                    
                check_x, check_y, check_z = x + dx, y + dy, z + dz
                block_type = getblock(check_x, check_y, check_z)
                
                if is_ore_block(block_type):
                    ore_blocks.append((check_x, check_y, check_z, block_type))
    
    return ore_blocks

def is_ore_block(block_type):
    """Check if a block is an ore"""
    if not block_type:
        return False
    
    ore_keywords = ["_ore", "coal", "iron", "gold", "diamond", "emerald", 
                   "lapis", "redstone", "copper", "ancient_debris"]
    
    block_lower = block_type.lower()
    return any(ore in block_lower for ore in ore_keywords)

def mine_ore_vein(start_position, max_blocks=20):
    """Mine an entire ore vein using flood fill algorithm"""
    if not mining_active:
        return
        
    echo(f"Found ore vein! Mining {max_blocks} blocks maximum...")
    
    mined_blocks = 0
    visited = set()
    queue = [start_position]
    
    while queue and mined_blocks < max_blocks and mining_active:
        if not mining_active:
            break
            
        x, y, z = queue.pop(0)
        
        if (x, y, z) in visited:
            continue
            
        visited.add((x, y, z))
        
        block_type = getblock(x, y, z)
        if not is_ore_block(block_type):
            continue
        
        # Move to and mine this ore block
        if mine_single_ore_block(x, y, z):
            mined_blocks += 1
            echo(f"Mined ore {mined_blocks}/{max_blocks}: {block_type}")
            
            # Check adjacent blocks for more ore
            directions = [
                (1, 0, 0), (-1, 0, 0),  # right, left
                (0, 1, 0), (0, -1, 0),  # up, down
                (0, 0, 1), (0, 0, -1)   # forward, backward
            ]
            
            for dx, dy, dz in directions:
                new_x, new_y, new_z = x + dx, y + dy, z + dz
                if (new_x, new_y, new_z) not in visited:
                    new_block_type = getblock(new_x, new_y, new_z)
                    if is_ore_block(new_block_type):
                        queue.append((new_x, new_y, new_z))
        
        # Small delay between blocks
        time.sleep(0.2)
    
    echo(f"Ore vein mining complete. Mined {mined_blocks} blocks.")

def mine_single_ore_block(x, y, z):
    """Mine a single ore block at the given coordinates"""
    if not mining_active:
        return False
        
    # Get current position
    current_x, current_y, current_z = player_position()
    
    # Calculate direction to look at the ore block
    dx = x - current_x
    dy = y - current_y
    dz = z - current_z
    
    # Calculate yaw and pitch to look at the block
    yaw = math.degrees(math.atan2(-dx, dz))
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    pitch = math.degrees(math.asin(-dy / distance)) if distance > 0 else 0
    
    # Look at the ore block
    player_set_orientation(yaw, pitch)
    time.sleep(0.2)
    
    # Mine the block
    player_press_attack(True)
    
    # Mine for longer for tough ores
    mine_time = 3.0  # 3 seconds for tough ores
    check_interval = 0.2
    
    for _ in range(int(mine_time / check_interval)):
        if not mining_active:
            player_press_attack(False)
            return False
            
        # Check if block is still there
        current_block = getblock(x, y, z)
        if not is_ore_block(current_block):
            break
            
        time.sleep(check_interval)
    
    player_press_attack(False)
    return True

def check_for_ores_and_mine(current_position):
    """Check for nearby ores and mine them if found"""
    if not mining_active:
        return False
        
    ore_blocks = get_ore_blocks_around(current_position, radius=2)
    
    if ore_blocks:
        echo(f"Found {len(ore_blocks)} ore blocks nearby!")
        
        # Save current position before mining ore vein
        vein_start_position = player_position()
        vein_start_orientation = player_orientation()
        
        # Mine the first ore block found (the vein)
        first_ore = ore_blocks[0]
        mine_ore_vein((first_ore[0], first_ore[1], first_ore[2]))
        
        # Return to original position and orientation
        if mining_active:
            echo("Returning to original mining position...")
            return_to_position(vein_start_position, vein_start_orientation)
        
        return True
    
    return False

def return_to_position(target_position, target_orientation):
    """Return to the original position and orientation"""
    if not mining_active:
        return
        
    current_pos = player_position()
    current_ori = player_orientation()
    
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
        player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.5)
        return
    
    # Otherwise, look toward target and move
    dx = target_x - current_x
    dz = target_z - current_z
    yaw = math.degrees(math.atan2(-dx, dz))
    
    player_set_orientation(yaw, 0)
    time.sleep(0.5)
    
    # Move toward target
    player_press_forward(True)
    
    while mining_active and distance > 1:
        current_pos = player_position()
        current_x, current_y, current_z = current_pos
        
        distance = math.sqrt(
            (target_x - current_x)**2 + 
            (target_y - current_y)**2 + 
            (target_z - current_z)**2
        )
        
        if distance <= 1:
            break
            
        time.sleep(0.1)
    
    player_press_forward(False)
    
    # Set final orientation
    if mining_active:
        player_set_orientation(target_orientation[0], target_orientation[1])
        time.sleep(0.5)


def check_gravel_block(yaw, pitch=20):
    """Check if the targeted block at given orientation is gravel"""
    if not mining_active:
        return False
        
    # Set orientation to check for gravel
    player_set_orientation(yaw, pitch)
    time.sleep(0.1)  # Brief pause for orientation to update
    
    # Get the targeted block
    targeted_block = player_get_targeted_block(max_distance=5)
    
    if targeted_block and targeted_block.type:
        return "gravel" in targeted_block.type.lower()
    return False

def gravel_mine():
    """Handle gravel mining with torch placement"""
    if not mining_active:
        return
        
    yaw, pitch = player_orientation()
    
    press_key_bind("key.hotbar.9", True)
    time.sleep(0.2)
    press_key_bind("key.hotbar.9", False)
    
    # Mine the gravel with extended time
    player_press_attack(True)
    # Check for stop during the 2-second gravel mining
    for _ in range(20):  # Check 20 times over 2 seconds
        if not mining_active:
            player_press_attack(False)
            return
        time.sleep(0.1)
    player_press_attack(False)
    
    # Switch back to pickaxe (hotbar slot 1)
    if mining_active:
        press_key_bind("key.hotbar.1", True)
        time.sleep(0.2)
        press_key_bind("key.hotbar.1", False)

def mine_at_angle(yaw, pitch, check_gravel=True):
    """Mine at specific angle, with optional gravel check"""
    if not mining_active:
        return False
        
    player_set_orientation(yaw, pitch)

    # Check for gravel if specified (only at pitch=20)
    if check_gravel and pitch == 20 and mining_active:
        if check_gravel_block(yaw, pitch):
            gravel_mine()
            return True  # Return True if gravel was handled
    
    # Normal mining with active check
    if mining_active:
        player_press_attack(True)
        # Check for stop during mining
        for _ in range(5):  # Check 5 times over 0.5 seconds
            if not mining_active:
                player_press_attack(False)
                return False
            time.sleep(0.1)
        player_press_attack(False)
    return False

def mining_time():
    global mining_active, original_position, original_orientation
    
    mining_active = True
    last_chat_check = time.time()
    last_ore_check = time.time()
    
    # Save original position and orientation
    original_position = player_position()
    original_orientation = player_orientation()
    
    echo("Mining script started with ore vein detection!")
    echo("Press T to stop. Will automatically mine ore veins.")
    
    try:
        while mining_active:
            current_time = time.time()
            
            # Check for T key press
            if current_time - last_chat_check > 0.1:
                screen = screen_name()
                if screen and "chat" in screen.lower():
                    echo("T pressed! Stopping mining script immediately.")
                    mining_active = False
                    break
                last_chat_check = current_time
            
            # Check for ores every 2 seconds
            if current_time - last_ore_check > 2.0:
                current_pos = player_position()
                if check_for_ores_and_mine(current_pos):
                    # If we mined an ore vein, update last check time
                    last_ore_check = time.time()
                    continue
                last_ore_check = current_time
            
            # Start mine_forward_1 but with interruptible steps
            if mining_active:
                yaw, pitch = player_orientation()
                # echo("Starting first mining cycle")
                player_press_sneak(True)
            
            # First cycle with forward
            if mining_active:
                player_press_forward(True)
            
            # Mine sequence - break into individual steps with checks
            mining_steps = [
                (yaw, 0, False), (yaw, 20, True), (yaw, 0, False), (yaw, 20, True)
            ]
            
            for step_yaw, step_pitch, check_gravel in mining_steps:
                if not mining_active:
                    break
                # Quick check for T before each mining action
                screen = screen_name()
                if screen and "chat" in screen.lower():
                    # echo("T pressed during mining! Stopping immediately.")
                    mining_active = False
                    break
                
                mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            if mining_active:
                player_press_forward(False)
            
            # Second cycle without forward
            if mining_active:
                mining_steps_2 = [(yaw, 0, False), (yaw, 20, True)]
                for step_yaw, step_pitch, check_gravel in mining_steps_2:
                    if not mining_active:
                        break
                    # Quick check for T before each mining action
                    screen = screen_name()
                    if screen and "chat" in screen.lower():
                        # echo("T pressed during mining! Stopping immediately.")
                        mining_active = False
                        break
                    
                    mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            # if mining_active:
            #     echo("First Cycle Complete")
            
            # Now do mine_forward_2 with the same interruptible pattern
            if mining_active:
                yaw, pitch = player_orientation()
                # echo("Starting second mining cycle")
            
            # Third cycle with forward
            if mining_active:
                player_press_forward(True)
            
            if mining_active:
                mining_steps_3 = [(yaw, 0, False), (yaw, 20, True), (yaw, 0, False), (yaw, 20, True)]
                for step_yaw, step_pitch, check_gravel in mining_steps_3:
                    if not mining_active:
                        break
                    # Quick check for T before each mining action
                    screen = screen_name()
                    if screen and "chat" in screen.lower():
                        echo("T pressed during mining! Stopping immediately.")
                        mining_active = False
                        break
                    
                    mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            if mining_active:
                player_press_forward(False)
            
            # Fourth cycle without forward
            if mining_active:
                mining_steps_4 = [(yaw, 0, False), (yaw, 20, True)]
                for step_yaw, step_pitch, check_gravel in mining_steps_4:
                    if not mining_active:
                        break
                    # Quick check for T before each mining action
                    screen = screen_name()
                    if screen and "chat" in screen.lower():
                        echo("T pressed during mining! Stopping immediately.")
                        mining_active = False
                        break
                    
                    mine_at_angle(step_yaw, step_pitch, check_gravel)
            
            # Final forward movement
            if mining_active:
                player_press_forward(True)
                for i in range(3): 
                    if not mining_active:
                        player_press_forward(False)
                        break
                    screen = screen_name()
                    if screen and "chat" in screen.lower():
                        echo("T pressed! Stopping immediately.")
                        mining_active = False
                        player_press_forward(False)
                        break
                    time.sleep(0.1)
                if mining_active:
                    player_press_forward(False)
            
            if mining_active:
                echo("Second Cycle Complete")
                
    finally:
        player_press_sneak(False)
        player_press_forward(False)
        player_press_attack(False)
        echo("Mining script stopped completely.")
        
mining_time()