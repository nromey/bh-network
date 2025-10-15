---
layout: default
title: Blind Hams Solar Dashboard
permalink: /solar/
---

# Blind Hams Solar Dashboard

Welcome to the Blind Hams Solar data hub. This page mirrors the snapshot on the home page, adds quick reference explanations for each metric, and will grow to include propagation calculators and MUF tools.

{% include home_solar_card.html %}

## What the Numbers Mean

- [Solar Flux Index (SFI)]({{ '/solar/sfi/' | relative_url }}) — how much energy the Sun is pumping into the ionosphere for HF work.
- [Sunspot Number]({{ '/solar/sunspot/' | relative_url }}) — how many active regions are on the disk and how large they are.
- [K and A Indices]({{ '/solar/kp/' | relative_url }}) — short-term geomagnetic activity that drives band stability.
- [GOES X-ray Flux]({{ '/solar/xray/' | relative_url }}) — flare monitoring that hints at sudden absorption or blackout risk.
- [Solar Wind Basics]({{ '/solar/solar-wind/' | relative_url }}) — speed, density, and temperature of the charged particles washing over Earth.
- [Flare & Proton Forecasts]({{ '/solar/flares/' | relative_url }}) — daily probabilities for C/M/X-class flares and 10&nbsp;MeV proton events.
- Noise Estimate — derived from the planetary and Boulder K indices to hint at expected band noise in S-units.

## Flare Outlook & Proton Events

The card above summarizes NOAA’s day-one probabilities for C-, M-, and X-class flares along with the 10&nbsp;MeV proton outlook. Higher percentages mean a greater risk of daytime HF fadeouts or polar absorption. Use the new [flare forecast page]({{ '/solar/flares/' | relative_url }}) for quick refresher notes while we build richer charts and alerts.

## Coming Soon

- Personal MUF lookups that use your stored location or a manual grid square.
- Band suggestions based on current SFI, Kp/Ap, and near-term forecast guidance.
- Archive view so you can review space-weather leading into large events.

Have ideas or questions? [Drop the Blind Hams crew a note]({{ '/contact/' | relative_url }}) so we can make this page more useful on the air.
