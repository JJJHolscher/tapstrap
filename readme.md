---
created_datetime: 2023-04-11T12:29:00
---

# TAPSTRAP

A daemon that allows your tapstrap to have an arbitrarily complex layout.

## status

I'm not affiliated with [tap-with-us](https://www.tapwithus.com/) and receive no payment for making this.
I just want my own tapstrap to be useable in a more complex environment than the defaults allow.
Expect me to be slow to address any issues without monetary incentives.

## features

- Connect multiple tapstrap devices.
- Use your `~/.XCompose` file.
- Layouts with arbitrary many modes.

## install

Make sure [xdotool](https://github.com/jordansissel/xdotool) is installed.

```sh
python -m venv --prompt tapstrap .venv
. .venv/bin/activate
pip install -r requirements.txt
mkdir -p "$HOME/.config/tapstrap"
cp ./layout.csv "$HOME/.config/tapstrap"
```

## usage

```
. .venv/bin/activate
python main.py
```

Or supply some command line arguments:

* `--bluetooth_addresses "A0:11:C2:3D:EE,AB:CD:DE:FG:HI"` these need to be specified if you want to connect multiple tapstraps.
* `--layout "/path/to/your_layout.csv"`
* `--xcompose "/path/to/your_xcompose` [compose man page](https://man.archlinux.org/man/Compose.5) make sure your .XCompose has no duplicate mappings.
* `--debug` starts an interactive debug session with [debugpy](https://github.com/microsoft/debugpy/)
* `--verbose` prints [bleak](https://github.com/hbldh/bleak)s messy logging messages to stderr. Good for debugging bluetooth connection issues.

## layout

My layout is here supplied under `layout.csv`.
The first column is not read by `main.py`.
The first row supplies the mode names.
The second column is the default mode, when switching to another mode and tapping a character without locking the now mode will set the tapstrap back to this mode.
When making your own adjustments to this file, the order of the rows cannot be changed since the row number maps to the signal tapstrap sends.

### supplied layout

My layout is very similar to the default layout of the tapstrap (if you disregard the mode). Here are the most important differences:

* enter has become ctrl, double ctrl is an enter
* when pressing a modifier twice, it releases the modifier and presses another key, unless the first pressing of that modifier was uppercase, in which case only the modifier gets released
  * double ctrl taps enter
  * double shift presses alt
  * double alt (quadruple shift) resets the mode and releases all modifiers
* switching to `num` mode also presses `SHIFT`, which is preferable for most programming related tasks. (this is why you don't see the . or , in my layout)
* switching to any mode will exit that mode after tapping a non-mode, non-modifier key, since you rarely need to type two consecutive special characters
* any mode in uppercase locks you in that mode until `set` resets you.
* `set` locks you in the current mode, another `set` resets you to the default mode.
* `compose` starts the compose mode
* a single tap can result in multiple keys, in the csv these are separated by whitespace
* type a number in `num` mode by tapping the binary representation of that number starting from your pinky :)

## limitations

### linux only

If you pay me I might through to the trouble of porting this to Mac and Windows.
Otherwise you can send pull requests which might or might not take multiple weeks for me to accept.
Otherwise I'll link your own fork or repo here, without promising that I actually looked at it.

Going about it yourself involves replacing any instance of `os.system("xdotool ...")` and the fact that [tap-sdk-python](https://github.com/TapWithUs/tap-python-sdk) uses different versions of [bleak](https://github.com/hbldh/bleak) for different platforms.

### (dis)connect delay

It will take a couple of seconds before `main.py` observes a tapstrap connect or disconnect.
This means that for a few seconds, your tapstrap will by in typing mode, which uses the default layout.
This delay is due to the fact that the linux version of the [tap-sdk-python](https://github.com/TapWithUs/tap-python-sdk) relies on a (very) old version of [bleak](https://github.com/hbldh/bleak).

### tap input delay (hardware limitation)

If you haven't typed any character for a second or two, the next tap takes a few 100 ms to register. This is inherent to the tapstrap as it also occurs without using this script.

## todo

- [ ] publish on pypi
