---
layout: default
title: CQ Blind Hams Podcast
permalink: /cq-blind-hams/
---

# CQ Blind Hams

The CQ Blind Hams podcast shares accessible techniques, demos, and tips for operating amateur radio as a blind or low‑vision ham. You can find episodes on Apple Podcasts, Spotify, and YouTube, and we mirror new releases as posts here with an embedded audio player.

## Episodes

{% assign cqbh_posts = site.posts | where_exp: "post", "post.categories contains 'cqbh'" %}
{% assign cqbh_sorted = cqbh_posts | sort: 'date' | reverse %}

{% if cqbh_sorted and cqbh_sorted.size > 0 %}
{% for post in cqbh_sorted %}
- [{{ post.title }}]({{ post.url | relative_url }})  
  *{{ post.date | date: "%B %-d, %Y" }}*  
  {{ post.excerpt | strip_html | strip_newlines | truncate: 220 }}
{% endfor %}
{% else %}
_No CQ Blind Hams posts yet. Check back soon!_
{% endif %}

