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

{% if site.widgets.news_preview %}
<section role="region" aria-labelledby="home-news">
  <h2 id="home-news">News</h2>

  {%- assign site_news = site.posts | where_exp: "post", "post.categories contains 'news' and post.categories contains 'bhdn'" -%}
  {%- assign cqbh_news = site.posts | where_exp: "post", "post.categories contains 'news' and post.categories contains 'cqbh'" -%}

  {%- assign latest_site_news = site_news | sort: 'date' | last -%}
  {% if latest_site_news %}
    <h3><a href="{{ latest_site_news.url | relative_url }}">{{ latest_site_news.title }}</a></h3>
    <p><em>{{ latest_site_news.date | date: "%B %-d, %Y" }}</em></p>
    <p>{{ latest_site_news.excerpt | strip_html | strip_newlines | truncate: 300 }}
    <a href="{{ latest_site_news.url | relative_url }}">Read more →</a></p>
  {% else %}
    <p><em>No site news yet. Check back soon!</em></p>
  {% endif %}

  {% assign latest_cqbh = cqbh_news | sort: 'date' | last %}
  {% if latest_cqbh %}
    <h3>Latest CQ Blind Hams Episode</h3>
    <p><a href="{{ latest_cqbh.url | relative_url }}">{{ latest_cqbh.title }}</a> — <em>{{ latest_cqbh.date | date: "%B %-d, %Y" }}</em></p>
  {% endif %}
</section>
{% endif %}


## What’s coming, the to-do list
- Up-to-the-minute solar data and a calculated MUF based on your location, presented in a clean, accessible format.
- Organized, filterable info on accessible radios and accessibility tips for various rigs.
- A files area where you can download (and submit) useful ham-radio software and data.

## What you can do today
- Browse current nets on our network (and a few partner nets). If we’re missing one, let us know! The new system makes it super easy to add them so don't be shy, the sky's the limit!
- Bored? Want to see something cool that took way too long to make but looks positively normal? Check the dynamically generated NCO rotation for our flagship Saturday morning net:
  **[The Blind Hams Digital Net — Nifty NER&trade;'s NCO Schedule](/nets/blind-hams/nco-schedule/)**

<section class="stats-section" role="region" aria-labelledby="site-stats-heading">
  <h2 id="site-stats-heading">Site Stats</h2>
  <p class="visit-counter">
    Home visits: <span id="home-visit-total">—</span>
    <span aria-hidden="true"> • </span>
    This month: <span id="home-visit-month">—</span>
  </p>
  <script defer src="{{ '/assets/js/visit-counter.js' | relative_url }}?v={{ site.time | date: '%s' }}"></script>
  <noscript>Enable JavaScript to see visit counts.</noscript>
  <p><small>Counts update automatically and reset monthly in the site time zone.</small></p>
  
</section>

---

Questions, ideas, or something we should add? We’d love to hear from you.

**73,**  
**K5NER** — Webmaster and Net Manager, Blind Hams Network
