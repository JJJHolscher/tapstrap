#!/usr/bin/python
import asyncio
import logging
import os
import platform
import sys
from argparse import ArgumentParser
from collections import OrderedDict
from time import time
from pathlib import Path

from bleak.exc import BleakError
from tapsdk import TapInputMode, TapSDK

NAME_TO_SYMBOL = {
    "comma": ",",
    "period": ".",
    "slash": "/",
    "semicolon": ";",
    "apostrophe": "'",
    "bracketleft": "[",
    "bracketright": "]",
    "backslash": "\\",
    "minus": "-",
    "equal": "=",
    "grave": "`",
    "space": " ",
    "underscore": "_",
    "plus": "+",
    "asterisk": "*",
    "less": "<",
    "greater": ">",
    "question": "?",
    "colon": ":",
    "quotedbl": '"',
    "braceleft": "{",
    "braceright": "}",
    "bar": "|",
    "numbersign": "#",
    "dollar": "$",
    "percent": "%",
    "ampersand": "&",
    "parenleft": "(",
    "parenright": ")",
    "at": "@",
    "asciitilde": "~",
    "exclam": "!",
    "asciicircum": "^",
    "dead_abovedot": "˙",
    "underbar": "_",
    "breve": "˘",
    "macron": "¯",
    "XP_Divide": "/",
    "diaeresis": "¨",
    "cedilla": "¸",
}
SYMBOL_TO_NAME = {v: k for k, v in NAME_TO_SYMBOL.items()}

class Keyboard:
    """
    The tapstrap sends 1 number per tap. This is here mapped
    to one or multiple keys that are handled consecutively.

    Any mode key switches this Keyboard to a different layout.
    Any modifier key is presses untill a character is tapped.
    Any character key is tapped, releases all modifiers
    and resets the mode unless the mode was uppercase.
    Also see __call___.
    """
    def __init__(self, map_file, xcompose_file):
        super().__init__()
        self.stack = []
        self.mappings = OrderedDict()
        self.compositions = create_composition(xcompose_file)
        self.composing = None
        self.caps_lock = False

        # Load mappings from a layout file.
        with open(map_file) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if i == 0:
                    for mode in line.split(",")[1:]:
                        self.mappings[mode] = []
                else:
                    for raw_keys, mode in zip(line.split(",")[1:], iter(self.mappings)):
                        keys = []
                        for key in raw_keys.split(" "):
                            key = key.strip()
                            if key in SYMBOL_TO_NAME:
                                key = SYMBOL_TO_NAME[key]
                            keys.append(key)
                        self.mappings[mode].append(tuple(keys))

        self.first_mode = next(iter(self.mappings))
        self.mode = self.first_mode

    def __call__(self, _, num):
        print(self.mode, num, self.stack, sep="\t", end="\t", flush=True)
        for key in self.mappings[self.mode.lower()][num - 1]:
            print(key, end=" ", flush=True)
            button = None

            if key == "mode":
                modes = iter(self.mappings)
                next(modes)
                if "ctrl" in self.stack:
                    next(modes)
                    key = next(modes)
                if "alt" in self.stack:
                    next(modes)
                    next(modes)
                    key = next(modes)
                else:
                    key = next(modes)

            # The key requests a mode switch.
            if type(key) == str and key.lower() in self.mappings:
                self.mode = key

            # The key is a modifier.
            elif key.lower() in {"ctrl", "alt", "shift", "super"}:
                button = self.press(key)

            # The key is character.
            else:
                button = key

            # Reset state if the tap was a character.
            if button:
                print(button, end="\t", flush=True)
                if self.composing:
                    self.compose(button)
                else:
                    self.tap(button)

                self.clear_stack()

        print()

    def compose(self, key):
        """
        Compose a character from a sequence of keys.
        If the sequence completed or the key is not part of any sequence, stop composing.
        """
        if key in self.composing:
            if self.caps_lock:
                key = key.upper()
            self.composing = self.composing[key]
        else:
            self.composing = None
            self.tap(key)

        if type(self.composing) == str:
            self.tap(self.composing)
            self.composing = None

    def press(self, raw_mod):
        # Pressing a modifier twice has special meaning.
        mod = raw_mod.lower()
        if mod in self.stack:
            self.release(mod)
            del self.stack[self.stack.index(mod)]

            if mod == "shift":
                return self.press("alt")
            elif mod == "ctrl":
                return "enter"
            elif mod == "alt":
                return "reset"
            elif mod == "super":
                self.caps_lock = not self.caps_lock
                return "Caps_Lock"

        # If the upper version of the modifier is in the stack, remove the modifier.
        elif mod.upper() in self.stack:
            self.release(mod)
            del self.stack[self.stack.index(mod.upper())]
            return

        else:
            self.stack.append(raw_mod)
            os.system(f"xdotool keydown {mod}")

    def clear_stack(self):
        for mod in self.stack:
            self.release(mod)
        self.stack = []
        if self.mode.lower() == self.mode:
            self.mode = "abc"

    def release(self, key):
        os.system(f"xdotool keyup {key}")

    def tap(self, key):
        if key == "set":
            if self.mode.lower() == self.mode:
                self.mode = self.mode.upper()
            else:
                self.mode = self.first_mode
            
        elif key == "compose":
            # ctrl + compose is ctrl +  enter
            if "ctrl" in self.stack:
                os.system("xdotool key enter")
            else:
                self.composing = self.compositions

        elif len(key) == 1:
            os.system(f"xdotool type {key}")

        else:
            os.system(f"xdotool key {key}")


def create_composition(xcompose_file):
    """ Create a dictionary of compositions from a xcompose file. """
    compositions = {}

    def add_composition(keys, symbol):
        c = compositions
        for i, key in enumerate(keys):
            if key not in c:
                if i == len(keys) - 1:
                    try:
                        c[key] = symbol
                    except TypeError:
                        print(keys, "cannot map to", symbol, "for it is already", c)
                else:
                    c[key] = {}
            c = c[key]

    if not os.path.exists(xcompose_file):
        print("No .XCompose file found, continuing without composition functionality.")
        return {}

    with open(xcompose_file) as f:
        for l in f:
            l = l.strip().split()
            if len(l) == 0 or l[0] != "<Multi_key>":
                continue

            i = 1
            key = l[i]
            keys = []
            while key != ":":
                if key[-1] == ":":
                    keys.append(key[1:-2])
                    break
                keys.append(key[1:-1])
                i += 1
                key = l[i]
            symbol = l[i + 1][1:-1]
            add_composition(keys, symbol)

    return compositions


def get_logger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return root


async def maintain_connection(loop, addresses, keyboard_controller):
    devices = {a: None for a in addresses}

    while True:
        for address, device in devices.items():
            if device:
                try:
                    async with asyncio.timeout(1):
                        await device.client.is_connected()
                    await asyncio.sleep(1)
                except TimeoutError:
                    await device.input_mode_refresh.stop()
                    del device
                    devices[address] = None
                    print(f"- {address}")
            else:
                device = TapSDK(address, loop)
                try:
                    async with asyncio.timeout(3):
                        connected = await device.client.connect_retrieved()
                except (TypeError, BleakError, TimeoutError) as e:
                    await device.client.disconnect()
                    connected = False
                if connected:
                    print(f"+ {address}")
                    await device.set_input_mode(TapInputMode("controller"))
                    await device.register_tap_events(keyboard_controller)
                    devices[address] = device


def cli():
    parser = ArgumentParser()
    parser.add_argument("--bluetooth_addresses", default="")
    parser.add_argument("--layout", default=str(Path.home() / ".config" / "tapstrap" / "layout.csv"))
    parser.add_argument("--xcompose", default=str(Path.home() / ".XCompose"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not args.bluetooth_addresses:
        args.bluetooth_addresses = TapSDK().address

    return args

if __name__ == "__main__":
    args = cli()
    if args.debug:
        import debugpy

        debugpy.listen(5678)
        print("--- waiting for debugpy client to connect on 5678 ... ", end="", flush=True)
        debugpy.wait_for_client()
        print("connected. waiting to continue ... ", end="", flush=True)
        breakpoint()
        print("starting program ---")
    if args.verbose:
        get_logger()

    print("mode", "num", "stack", "keys and buttons", sep="\t")
    kb = Keyboard(args.layout, args.xcompose)
    loop = asyncio.get_event_loop()
    loop.create_task(maintain_connection(loop, args.bluetooth_addresses.split(","), kb))
    loop.run_forever()
