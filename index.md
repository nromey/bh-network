---
layout: default
title: Blind Hams Digital Network Home
---

{% if site.widgets.connect_banner %}
{% include notice_banner.html id="connect" title="How to connect to the Blind Hams Network" md="how_to_connect.md" %}
{% endif %}

# Welcome to the Blind Hams Digital Network!

The **Blind Hams Digital Network** is a community built by and for blind and visually impaired amateur radio operators. While many of our conversations highlight accessibility and tools that work well for us, **all licensed radio amateurs are welcome** to join in.  

{% include home_next_nets.html %}

## News

{% assign latest = site.posts | sort: 'date' | last %}
{% if latest %}
### [{{ latest.title }}]({{ latest.url | relative_url }})
*{{ latest.date | date: "%B %-d, %Y" }}*

{{ latest.excerpt | strip_html | strip_newlines | truncate: 300 }}
[Read more →]({{ latest.url | relative_url }})
{% else %}
_No news posts yet. Check back soon!_
{% endif %}


## What’s coming, the to-do list
- Up-to-the-minute solar data and a calculated MUF based on your location, presented in a clean, accessible format.
- Organized, filterable info on accessible radios and accessibility tips for various rigs.
- A files area where you can download (and submit) useful ham-radio software and data.

## What you can do today
- Browse current nets on our network (and a few partner nets). If we’re missing one, let us know! The new system makes it super easy to add them so don't be shy, the sky's the limit!
- Bored? Want to see something cool that took way too long to make but looks positively normal? Check the dynamically generated NCO rotation for our flagship Saturday morning net:
  **[The Blind Hams Digital Net — Nifty NER&trade;'s NCO Schedule](/nets/blind-hams/nco-schedule/)**

---

Questions, ideas, or something we should add? We’d love to hear from you.

**73,**  
**K5NER** — Webmaster and Net Manager, Blind Hams Network
