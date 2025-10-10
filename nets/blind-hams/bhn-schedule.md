---
layout: default
title: BHN Digital Net — NCO Schedule
permalink: /nets/blind-hams/nco-schedule/
---

{%- assign use_proxy = site.data_fetch.use_proxy | default: false -%}
{%- if use_proxy -%}
  {%- assign nco_src = site.data_endpoints.nco_12w_proxy | default: "/data/bhn_nco_12w.json" -%}
{%- else -%}
  {%- assign nco_src = site.data_endpoints.nco_12w | default: "https://data.blindhams.network/bhn_nco_12w.json" -%}
{%- endif -%}

<div class="nco-table-container" data-nco-json="{{ nco_src }}">
{% include nco_table.html schedule=site.data.bhn_ncos_schedule items_key="items" title="Blind Hams Digital Net — NCO Schedule" caption="Table that displays upcoming net operators for the Blind Hams Digital net" show_location=true %}
</div>

<script defer src="{{ '/assets/js/json-widgets.js' | relative_url }}?v={{ site.github.build_revision | default: site.time | date: '%s' }}"></script>
