# Minecraft Semi-AFK Strip Mining Script

A personal project of mine that I made for Minecraft that performs strip mining with **ore detection**, **fall recovery**, and **emergency safety features**.

## ✨ Features

### 🛡️ Safety Systems
- **Fall Detection & Recovery**: Real-time fall monitoring with automatic jump recovery
- **Stuck Detection**: Automatic recovery from stuck positions
  (useful in cases where there's a hole in front of you)
  
- **Lava Detection**: Emergency stop system when lava is detected
  (will protect you from lava 90% of the time, it will basically detect lava in the direction you're mining at and if it does, it presses back for 3 seconds and stops)
  
- **Gravel Handling**: Automatic detection and efficient gravel mining (put shovel in hotkey 9 slot and your pickaxe in hotkey 1)
- **Emergency Stop**: Press `T` to instantly stop the script

## 🚀 Installation

1. Ensure **Minescript** is installed and running in your Minecraft instance
2. Place the script in the appropriate Minescript scripts directory
3. Make sure all required Python modules are available

- **Minescript** Minecraft mod
- **Python 3.12**
- Required modules:
  - `visibility_scanner`
  - `aim.player_aim`
  - `math`, `threading`, `time`, `random`
    
  - `numba`, `numpy` 
  ```pip install --force-reinstall numba==0.61.2 llvmlite==0.44.0 numpy==2.2.6```

Refer to this repository for more details: (the credit for the ore mining and smooth + accurate aiming capabilities of this script goes to them. I couldn't have done it without their scanner)
https://github.com/Philogex/Minescript-Miner

## 🎮 Usage

### Starting the Script
Type in "\mining_script" inside minecraft chatbox and it will:

1. 🔒 Lock player orientation to the direction you're facing
2. 🏃 Begin strip mining while sneaking  
3. 🔍 Continuously scan for and mine ores
4. 📊 Monitor for hazards and handle them automatically

### Controls
- **`T` Key**: Emergency stop - opens chat and stops the script immediately
- The script handles all movement and mining automatically

### Mining Behavior
- Mines at two optimized pitch angles (0° and 20°) for maximum coverage
- Maintains forward movement while scanning surroundings  
- Automatically switches between strip mining and ore collection

## 🛡️ Safety Features

### 🪂 Fall Protection
- Monitors Y-level continuously
- Detects falls of 1+ blocks
- Automatically attempts recovery by jumping for 3 seconds
- Resumes mining after successful recovery

### 🌋 Lava Protection  
- Scans 3x3 area in front of player up to 4 blocks away
- Immediate emergency stop when lava detected
- Moves player backward and stops script

### 🪨 Gravel Handling
- Instant detection of gravel blocks
- Automatic switch to shovel (hotbar slot 9)
- Efficient mining and return to pickaxe (hotbar slot 1)

## ⚙️ Configuration

### Target Ores
The script mines these block types by default:
```python
target_ids = [
    "minecraft:diamond_ore",
    "minecraft:deepslate_diamond_ore", 
    "minecraft:coal_ore",
    "minecraft:iron_ore",
    "minecraft:gold_ore",
    # ... and more
]
```

### Mining Parameters
- **Reach Distance**: 4.8 blocks
- **Fall Check Interval**: 0.5 seconds  
- **Max Mining Time**: Varies by ore hardness
- **Stuck Detection**: 1-second movement checks

## 🚨 Troubleshooting

### Common Issues
1. **Script not starting**: Check Minescript installation and dependencies
2. **Player not moving**: Ensure no chat is open and T key isn't pressed  
3. **Ores not being mined**: Verify target ore list matches your Minecraft version

### Emergency Stop
If the script behaves unexpectedly:
1. Press `T` to open chat and stop immediately
2. All movement keys will be released
3. Script state will be reset

## ⛏️ Best Conditions
- Efficiency IV or V, Unbreaking III, Fortune/Silk Touch, Mending Diamond/Netherite Pickaxe
- Pickaxe on Hotkey 1 and Shovel on Hotkey 9 (can be changed inside the file)
- Overworld Y -59

If you have swift sneak on your leggings, find this line:
```
# CONTINUOUS MOVEMENT STUCK CHECK
        current_time = time.time()
        if current_time - movement_check_start >= 1.0  
```
Change 1.0 to 2.0 since it might interfere a bit while mining with those frequent movement checks.

(Not designed for mining in the Nether just yet, will work on it soon)


## ⚠️ Disclaimer

Use this script responsibly and in accordance with Minecraft's EULA and server rules. I'm not responsible for any issues caused by using this automation tool.
I'm simply here to share my work.

---

> **Note**: This script is designed for single-player worlds or servers where automation is permitted. Always respect server rules and other players' experiences.
