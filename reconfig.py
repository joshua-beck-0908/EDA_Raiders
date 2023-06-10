import os

def setcfg(name):
    try:
        with open(f'setup_{name}.toml', 'r') as f:
            cfg = f.read()
    except:
        cfg = None
        
    if cfg:
        with open('settings.toml', 'w') as f:
            f.write(cfg)
        print(f'Config set to {name}.')
    else:
        print(f'Config {name} not found.')
