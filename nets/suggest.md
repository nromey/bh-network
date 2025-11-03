---
layout: default
title: Suggest a Net
permalink: /nets/suggest/
---

# Suggest a Net

Do you know about a net that belongs on BlindHams.network? Fill out this form and our editors will review it. Please share as much detail as you can&mdash;we'll follow up if we need clarification.

Your submission will appear in our moderation queue. Nothing goes live until a publisher approves it.

<style>
.suggest-net-form {
  display: grid;
  gap: 1.5rem;
  max-width: 48rem;
}
.suggest-net-form fieldset {
  border: 1px solid #d1d5db;
  border-radius: 0.75rem;
  padding: 1.25rem;
}
.suggest-net-form legend {
  font-weight: 600;
}
.suggest-net-form label {
  display: block;
  margin-top: 0.75rem;
  font-weight: 600;
}
.suggest-net-form input,
.suggest-net-form textarea,
.suggest-net-form select {
  width: 100%;
  margin-top: 0.35rem;
  padding: 0.6rem;
  font-size: 1rem;
}
.weekday-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.weekday-grid label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0;
  font-weight: 500;
}
.hint {
  font-size: 0.95rem;
  color: #4b5563;
}
.submission-status {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-weight: 500;
}
.submission-status--success {
  border: 1px solid #047857;
  background: #ecfdf5;
  color: #065f46;
}
.submission-status--error {
  border: 1px solid #b91c1c;
  background: #fef2f2;
  color: #7f1d1d;
}
.visually-hidden {
  position: absolute;
  left: -10000px;
  width: 1px;
  height: 1px;
  overflow: hidden;
}
.primary {
  align-self: start;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border-radius: 0.5rem;
  border: none;
  background: #2a6ad1;
  color: #fff;
  cursor: pointer;
}
.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

<form id="suggestNetForm" class="suggest-net-form" novalidate>
  <fieldset>
    <legend>Net details</legend>
    <label for="netName">Net name <span aria-hidden="true">*</span></label>
    <input type="text" id="netName" name="name" required>

    <label for="netDescription">What is this net about? <span aria-hidden="true">*</span></label>
    <textarea id="netDescription" name="description" rows="4" required></textarea>

    <label for="netCategory">Category <span aria-hidden="true">*</span></label>
    <select id="netCategory" name="category" required>
      <option value="bhn">Blind Hams</option>
      <option value="disability">Disabilities</option>
      <option value="general">General Interest</option>
    </select>

    <label for="startTime">Start time <span aria-hidden="true">*</span></label>
    <input type="time" id="startTime" name="start_local" required>

    <label for="durationMinutes">Duration (minutes) <span aria-hidden="true">*</span></label>
    <input type="number" id="durationMinutes" name="duration_min" min="1" step="1" required>

    <label for="timeZone">Net time zone <span aria-hidden="true">*</span></label>
    <select id="timeZone" name="time_zone" required>
      <option value="America/New_York">Eastern (America/New_York)</option>
      <option value="America/Chicago">Central (America/Chicago)</option>
      <option value="America/Denver">Mountain (America/Denver)</option>
      <option value="America/Los_Angeles">Pacific (America/Los_Angeles)</option>
      <option value="America/Phoenix">Arizona (America/Phoenix)</option>
      <option value="America/Anchorage">Alaska (America/Anchorage)</option>
      <option value="Pacific/Honolulu">Hawaii (Pacific/Honolulu)</option>
      <option value="Europe/London">UK (Europe/London)</option>
      <option value="Europe/Paris">Central Europe (Europe/Paris)</option>
      <option value="Europe/Berlin">Central Europe (Europe/Berlin)</option>
      <option value="UTC">UTC / Zulu</option>
    </select>
  </fieldset>

  <fieldset>
    <legend>Recurrence</legend>
    <p class="hint">Pick the option that matches the net schedule. We’ll convert it into a technical format for you.</p>

    <label for="recurrenceType">How often does the net meet?</label>
    <select id="recurrenceType" name="recurrence_type">
      <option value="weekly">Weekly</option>
      <option value="monthly">Monthly</option>
    </select>

    <div id="weeklyRecurrence" class="recurrence-pane">
      <p>Which day(s) each week?</p>
      <div class="weekday-grid" role="group" aria-labelledby="weeklyRecurrence">
        <label><input type="checkbox" value="MO"> Monday</label>
        <label><input type="checkbox" value="TU"> Tuesday</label>
        <label><input type="checkbox" value="WE"> Wednesday</label>
        <label><input type="checkbox" value="TH"> Thursday</label>
        <label><input type="checkbox" value="FR"> Friday</label>
        <label><input type="checkbox" value="SA"> Saturday</label>
        <label><input type="checkbox" value="SU"> Sunday</label>
      </div>
    </div>

    <div id="monthlyRecurrence" class="recurrence-pane" hidden aria-hidden="true">
      <label for="monthlyPosition">Which week of the month?</label>
      <select id="monthlyPosition" name="monthly_position">
        <option value="1">First</option>
        <option value="2">Second</option>
        <option value="3">Third</option>
        <option value="4">Fourth</option>
        <option value="-1">Last</option>
      </select>

      <label for="monthlyWeekday">Which weekday?</label>
      <select id="monthlyWeekday" name="monthly_weekday">
        <option value="MO">Monday</option>
        <option value="TU">Tuesday</option>
        <option value="WE">Wednesday</option>
        <option value="TH">Thursday</option>
        <option value="FR">Friday</option>
        <option value="SA">Saturday</option>
        <option value="SU">Sunday</option>
      </select>
    </div>

    <p class="hint">If the exact pattern isn’t listed, pick the closest option and mention the details in the “Additional info” box below.</p>
    <input type="hidden" name="rrule" id="rruleField" required>
  </fieldset>

  <fieldset>
    <legend>Connections</legend>
    <p class="hint">Share the main way people join this net. You can add more detail in “Additional info.”</p>

    <label for="allstarNode">AllStar node(s)</label>
    <input type="text" id="allstarNode" name="allstar" placeholder="e.g., 50631, 42726">

    <label for="echolinkNode">EchoLink node(s)</label>
    <input type="text" id="echolinkNode" name="echolink" placeholder="e.g., *KV3T-L">

    <label for="hfFrequency">HF frequency</label>
    <input type="text" id="hfFrequency" name="frequency" placeholder="e.g., 14.200 MHz">

    <label for="hfMode">HF mode</label>
    <input type="text" id="hfMode" name="mode" placeholder="e.g., USB, CW, FT8">
    <p class="hint">If the net uses Zoom, Teams, DMR, or anything else, mention it in “Additional info.”</p>
  </fieldset>

  <fieldset>
    <legend>Additional info</legend>
    <label for="additionalInfo">Anything else we should know?</label>
    <textarea id="additionalInfo" name="additional_info" rows="4" placeholder="Zoom link, DMR talkgroup, host details, etc."></textarea>
  </fieldset>

  <fieldset>
    <legend>Your contact information</legend>
    <p class="hint">We’ll only use this if we have questions about your submission.</p>

    <label for="contactName">Your name</label>
    <input type="text" id="contactName" name="contact_name">

    <label for="contactEmail">Email <span aria-hidden="true">*</span></label>
    <input type="email" id="contactEmail" name="contact_email" required>
  </fieldset>

  <div class="visually-hidden">
    <label for="website">Leave this field empty</label>
    <input type="text" id="website" name="website" tabindex="-1" autocomplete="off">
  </div>

  <button type="submit" class="primary">Submit net for review</button>
  <div id="submissionStatus" role="status" aria-live="polite"></div>
</form>

<p><a href="/nets/">Back to nets</a></p>

<script src="/assets/js/suggest-net.js"></script>
