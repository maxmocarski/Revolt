# ReVolt: E-Waste Scanner

Revolt is an open-source e-waste scanner, that helps people properly dispose of old electronics, its privacy first, with the AI models it rusn beign locacl and not messing about with the cloud. It was bulit for the Congressional App Challange for CT-04
Revolts Porpose is to use locally hosted vision models, gemma via ollama, to analyze computer components, idenitfy if those componets have hazardous materials, flag prescious metals, like gold and to give information on local disposal and recyclign guidlines and where to dispose of the electronic devices, from 80 inch plasma tvs, to microsds, this will tell you what the object is and what you can do with it, with **NO** cloud dependance.

## Architecture

- **Frontend:** Streamlit (Python)
- **AI Vision Engine:** Ollama (`Gemma-vision`) running locally
- **Backend Infrastructure:** Python, Docker, systemd
- **Networking:** Local network access via Tailscale / MagicDNS

## Quickstart

1. **Pull the vison model**
