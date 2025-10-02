---
layout: default
title: "News and Other Miscellaneous Happenings"
permalink: /news/
---

# News

{%- assign cqbh_posts = site.posts | where_exp: "post", "post.categories contains 'news' and post.categories contains 'cqbh'" -%}
{%- assign site_news_posts = site.posts | where_exp: "post", "post.categories contains 'news' and post.categories contains 'bhdn'" -%}

<section class="news-section" id="site-news" data-pager data-default-size="5" data-pager-focus="heading" aria-labelledby="site-news-heading">
  <h2 id="site-news-heading">Site News</h2>
  <p>
    <a class="skip-link" href="#site-news-pager">Skip to Site News pager</a>
    <a class="skip-link" href="#site-news-list">Skip to Site News list</a>
  </p>
  <div class="pager-shortcuts-toggle">
    <button type="button" data-pager-shortcuts-toggle aria-pressed="false">Enable keyboard shortcuts</button>
  </div>
  {%- if site_news_posts and site_news_posts.size > 0 -%}
  {%- assign site_news_sorted = site_news_posts | sort: 'date' | reverse -%}
  <form class="pager-search" role="search" aria-label="Search site news posts">
    <label for="site-news-search">Search posts</label>
    <input id="site-news-search" type="search" placeholder="e.g., policy, release, net updates" data-pager-search>
    <button type="button" data-pager-search-clear aria-label="Clear search">Clear</button>
  </form>
  <form class="pager-cats" aria-label="Filter by category">
    <label for="site-news-cat">Filter by category</label>
    <select id="site-news-cat" data-pager-cat-select>
      <option value="">Choose category</option>
    </select>
    <button type="button" data-pager-cat-add>Add</button>
    <button type="button" data-pager-cat-clear>Clear</button>
    <div class="pager-cat-active" data-pager-cat-active aria-live="polite" aria-atomic="true"></div>
  </form>
  <div class="pager-toolbar">
    <span class="pager-label">Items per page</span>
    <div class="pager-size-buttons" role="group" aria-label="Items per page">
      <button type="button" data-pager-size-btn="5" aria-pressed="true">5</button>
      <button type="button" data-pager-size-btn="10">10</button>
      <button type="button" data-pager-size-btn="20">20</button>
      <button type="button" data-pager-size-btn="all">All</button>
    </div>
    <nav class="pager-nav" id="site-news-pager" aria-label="Site News Pagination" aria-controls="site-news-list" aria-describedby="site-news-status" tabindex="-1">
      <button type="button" data-pager-first aria-label="First page">First</button>
      <button type="button" data-pager-prev aria-label="Previous page">Prev</button>
      <span data-pager-pages></span>
      <button type="button" data-pager-next aria-label="Next page">Next</button>
      <button type="button" data-pager-last aria-label="Last page">Last</button>
      <span class="pager-status" id="site-news-status" data-pager-status-visible></span>
      <span class="sr-only" role="status" aria-live="polite" aria-atomic="true" data-pager-status></span>
    </nav>
  </div>
  <p class="pager-help">Tip: To use shortcuts, turn off Browse Mode (NVDA) or Forms Mode (JAWS). Otherwise, use the buttons. Shortcuts: Left/Right or Page Up/Down; Home/End.</p>
  <ul class="news-list" id="site-news-list" data-pager-list tabindex="-1">
    {%- for post in site_news_sorted -%}
    {%- assign extra_cats = '' | split: '' -%}
    {%- for c in post.categories -%}
      {%- assign c_l = c | downcase -%}
      {%- if c_l != 'news' and c_l != 'bhdn' -%}
        {%- assign extra_cats = extra_cats | push: c -%}
      {%- endif -%}
    {%- endfor -%}
    {%- assign cats_attr = extra_cats | join: ',' -%}
    <li data-cats="{{ cats_attr }}">
      <h3 class="news-item-title"><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
      <p><em>{{ post.date | date: "%B %-d, %Y" }}</em></p>
      <p>{{ post.excerpt | strip_html | strip_newlines | truncate: 300 }}
      {%- if post.excerpt != post.content -%} <a href="{{ post.url | relative_url }}">Read more →</a>{%- endif -%}</p>
      {%- if post.tags and post.tags.size > 0 -%}<p><small>{{ post.tags | join: ", " }}</small></p>{%- endif -%}
    </li>
    {%- endfor -%}
  </ul>
  {%- else -%}
  <p><em>No site news posts yet.</em></p>
  {%- endif -%}
</section>

<section class="news-section" id="cqbh-news" data-pager data-default-size="5" data-pager-focus="heading" aria-labelledby="cqbh-news-heading">
  <h2 id="cqbh-news-heading">CQ Blind Hams</h2>
  <p>
    <a class="skip-link" href="#cqbh-news-pager">Skip to CQ Blind Hams pager</a>
    <a class="skip-link" href="#cqbh-news-list">Skip to CQ Blind Hams list</a>
  </p>
  <div class="pager-shortcuts-toggle">
    <button type="button" data-pager-shortcuts-toggle aria-pressed="false">Enable keyboard shortcuts</button>
  </div>
  {%- if cqbh_posts and cqbh_posts.size > 0 -%}
  {%- assign cqbh_sorted = cqbh_posts | sort: 'date' | reverse -%}
  <form class="pager-search" role="search" aria-label="Search CQ Blind Hams posts">
    <label for="cqbh-news-search">Search posts</label>
    <input id="cqbh-news-search" type="search" placeholder="e.g., FT-70, NanoVNA, TechZoom" data-pager-search>
    <button type="button" data-pager-search-clear aria-label="Clear search">Clear</button>
  </form>
  <form class="pager-cats" aria-label="Filter by category">
    <label for="cqbh-news-cat">Filter by category</label>
    <select id="cqbh-news-cat" data-pager-cat-select>
      <option value="">Choose category</option>
    </select>
    <button type="button" data-pager-cat-add>Add</button>
    <button type="button" data-pager-cat-clear>Clear</button>
    <div class="pager-cat-active" data-pager-cat-active aria-live="polite" aria-atomic="true"></div>
  </form>
  <div class="pager-toolbar">
    <span class="pager-label">Items per page</span>
    <div class="pager-size-buttons" role="group" aria-label="Items per page">
      <button type="button" data-pager-size-btn="5" aria-pressed="true">5</button>
      <button type="button" data-pager-size-btn="10">10</button>
      <button type="button" data-pager-size-btn="20">20</button>
      <button type="button" data-pager-size-btn="all">All</button>
    </div>
    <nav class="pager-nav" id="cqbh-news-pager" aria-label="CQ Blind Hams Pagination" aria-controls="cqbh-news-list" aria-describedby="cqbh-news-status" tabindex="-1">
      <button type="button" data-pager-first aria-label="First page">First</button>
      <button type="button" data-pager-prev aria-label="Previous page">Prev</button>
      <span data-pager-pages></span>
      <button type="button" data-pager-next aria-label="Next page">Next</button>
      <button type="button" data-pager-last aria-label="Last page">Last</button>
      <span class="pager-status" id="cqbh-news-status" data-pager-status-visible></span>
      <span class="sr-only" role="status" aria-live="polite" aria-atomic="true" data-pager-status></span>
    </nav>
  </div>
  <p class="pager-help">Tip: To use shortcuts, turn off Browse Mode (NVDA) or Forms Mode (JAWS). Otherwise, use the buttons. Shortcuts: Left/Right or Page Up/Down; Home/End.</p>
  <ul class="news-list" id="cqbh-news-list" data-pager-list tabindex="-1">
    {%- for post in cqbh_sorted -%}
    {%- assign extra_cats = '' | split: '' -%}
    {%- for c in post.categories -%}
      {%- assign c_l = c | downcase -%}
      {%- if c_l != 'news' and c_l != 'cqbh' -%}
        {%- assign extra_cats = extra_cats | push: c -%}
      {%- endif -%}
    {%- endfor -%}
    {%- assign cats_attr = extra_cats | join: ',' -%}
    <li data-cats="{{ cats_attr }}">
      <h3 class="news-item-title"><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
      <p><em>{{ post.date | date: "%B %-d, %Y" }}</em></p>
      <p>{{ post.excerpt | strip_html | strip_newlines | truncate: 300 }}
      {%- if post.excerpt != post.content -%} <a href="{{ post.url | relative_url }}">Read more →</a>{%- endif -%}</p>
      {%- if post.tags and post.tags.size > 0 -%}<p><small>{{ post.tags | join: ", " }}</small></p>{%- endif -%}
    </li>
    {%- endfor -%}
  </ul>
  {%- else -%}
  <p><em>No CQ Blind Hams posts yet.</em></p>
  {%- endif -%}
</section>

<script defer src="{{ '/assets/js/pager.js' | relative_url }}"></script>
