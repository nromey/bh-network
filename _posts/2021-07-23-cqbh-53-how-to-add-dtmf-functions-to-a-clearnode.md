---
layout: post
title: "New CQ Blind Hams Podcast: CQBH 53 How to add DTMF functions to a ClearNode"
date: 2021-07-23 19:33:46 +0000
categories: [news, cqbh]
tags: [podcast, CQ Blind Hams]
ableplayer: true
cqbh_guid: 369ea14e-5f01-497b-8bfd-d3e2da081804
---

A new episode of the CQ Blind Hams podcast is out: "CQBH 53 How to add DTMF functions to a ClearNode". You can listen on Apple Podcasts, Spotify, and YouTube; we’ve embedded the episode below for easy playback.

{% include able_audio.html title="CQBH 53 How to add DTMF functions to a ClearNode" src="https://anchor.fm/s/123c50ac/podcast/play/37722627/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-07-23%2F25076409d2b90bb34918606cb34a202b.m4a" fallback_url="https://anchor.fm/s/123c50ac/podcast/play/37722627/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-07-23%2F25076409d2b90bb34918606cb34a202b.m4a" %}

Description (from CQ Blind Hams):

<p>From NE5V</p>
<p>This is for anyone interested in adding DTMF Command functions to the ClearNode.</p>
<p>I was parusing the rpt.conf file in my ClearNode and found the following line at the end of the [functions stanza.</p>
<p>#includeifexitsts custom/my_dtmf_commands.conf</p>
<p>This line allows a user to add DTMF functions that won't go away when the ClearNode software is updated, or when a user changes which digital mode to use.</p>
<p>Here's how it works.</p>
<p>The statement assumes that there is a directory of the /etc/asterisk directory called "custom" and that in this directory is a file called "my_dtmf_commands_conf". Be sure to make all the letters in the directory and filename lower case, since that is the case specified in the #includeifexists statement.</p>
<p>One way to create the directory is through WINSCP. Go to the asterisk directory and once in that directory press F7 then enter "custom" as the directory name. Don't use the "".</p>
<p>If you choose to do this from the shell prompt, which is option 9 on the menu when you ssh to the node, do the following.</p>
<p>Go to the Asterisk directory by using</p>
<p>cd /etc/asterisk</p>
<p>Once there type</p>
<p>mkdir custom</p>
<p>This creates the custom directory.</p>
<p>Then use whatever method you want to create the file. I did it in Winscp by going to the custom directory, pressed shift+F4, and gave it the file name my_dtmf_commands</p>
<p>Another way is to go to the shell prompt after ssh into the node. This is option 9 on the menu. Then type</p>
<p>nano /etc/asterisk/custom/my_dtmf_commands</p>
<p>The entries in my file look like this.</p>
<p>D6=cop,32 ;Touchtone test. Enter digits with last as #</p>
<p>d7=cop,34 ; Telemetry Off</p>
<p>d8=cop,33 ; Telemetry on</p>
<p>d9=cop,35 ; Telemetry limited</p>
<p>The information after the ; explain what the commands do.</p>
<p>Save your work.</p>
<p>The next step is to make the files executible. Go to the custom directory. Then type</p>
<p>chmod + x my_dtmf_commands.conf</p>
<p>Then go to option 11 in the node menu which is the asterisk client. type</p>
<p>rpt reload</p>
<p>You then can execute the commands in the custom file. For example *D7 in my example turns off telemetry.</p>
<p>This apparently works only for adding functions, not overwriting them. I've been testing this, if I want to overwrite a function, the #includeifexists needs to be at the top of the stanza. I tried this in the telemetry stanza, because I wanted to overwrite the default courtesy tones. I put this at the top of the telemetry stanza</p>
<p>#includeifexists custom/my_telemetry.conf</p>
<p>I put the courtesy tones in the file using the methods above, and when I saved settings in the app, the new tones stayed.</p>
<p>This isn't Clearnode specific, but I thought it would be of interest, particularly to Clearnode users.</p>
<p><br></p>
<p>visit www.blindhams.com</p>
