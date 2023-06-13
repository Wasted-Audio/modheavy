# modgen
## A plugin builder for pure data files for the mod.audio device ecosystem

---
## Instructions
- Install docker for your environment (https://www.docker.com/)
- Clone this repository: `git clone https://github.com/Wasted-Audio/modheavy.git`
- Copy `.env.example` to `.env`
- Modify `.env` according to your needs. By default it will boostrap both **modduox** and **moddwarf** but you can disable whichever you don't need. You can also change the exposed port to something else
- Run `docker compose up -d modgen`. It will take some time the first time you run it, but should be almost instantaneous from then on
- Once it's up and running, visit http://127.0.0.1:5000 in your browser.

## Usage

- Save your heavy compatible patch in pure data.
- Visit http://127.0.0.1:5000 in your browser and select the file. Fill in the rest of the plugin info (name, brand, category, uri), select the device you want to build for and fill in the ip (the default ip for a device connected via USB is 192.168.51.1)
- If you want the options to be saved so that you don't have to fill them in each time, tick the **Save settings as default** checkbox.
- Press **Upload** and fingers crossed!
