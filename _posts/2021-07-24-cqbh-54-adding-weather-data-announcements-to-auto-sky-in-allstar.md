---
layout: post
title: "New CQ Blind Hams Podcast: CQBH 54 Adding weather data announcements to auto-sky in allstar"
date: 2021-07-24 11:12:14 +0000
categories: [news, cqbh]
tags: [podcast, CQ Blind Hams]
ableplayer: true
cqbh_guid: f4ce33d1-d145-4ab1-8137-4eca42c23771
---

A new episode of the CQ Blind Hams podcast is out: "CQBH 54 Adding weather data announcements to auto-sky in allstar". You can listen on Apple Podcasts, Spotify, and YouTube; we’ve embedded the episode below for easy playback.

{% include able_audio.html title="CQBH 54 Adding weather data announcements to auto-sky in allstar" src="https://anchor.fm/s/123c50ac/podcast/play/37749425/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-07-24%2Faa953b84cbe6f9a73dce5c293d610497.m4a" fallback_url="https://anchor.fm/s/123c50ac/podcast/play/37749425/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2021-07-24%2Faa953b84cbe6f9a73dce5c293d610497.m4a" %}

Description (from CQ Blind Hams):

<p>From NE5V</p>
<p>The weather_data.php script works as a companion to AutoSky. &nbsp;It is not a replacement. &nbsp;It uses AutoSky to obtain any information on warnings in your area.&nbsp;</p>
<p>Go to www.kd8tig.com/downloads and look for the file: &nbsp;weather_data.tgz. &nbsp;Then copy it to a directory on your node. &nbsp;I used /usr/local/sbin.</p>
<p>&nbsp;</p>
<p>A cleaner and faster way to get this is to ssh into your node, and in the directory of your choice execute the following command. &nbsp;I will use my example.</p>
<p>cd /usr/local/sbin</p>
<p>wget http://www.kd8tig.com/downloads/weather_data.tgz</p>
<p><br></p>
<p>Once you have this file in the /usr/local/sbin directory by using one of these methids do the following:</p>
<p><br></p>
<p>tar zxvf weather_data.tgz</p>
<p>&nbsp;</p>
<p>The resulting file is weather_data.php</p>
<p>&nbsp;</p>
<p>If you find that file, you need to make it executable. &nbsp;To do this type</p>
<p>Chmod + x weather_data.php</p>
<p>&nbsp;If you are not in the directory where the file exists then include the full pathname to the file such as /usr/local/sbin/weather_data.php</p>
<p>At this point, it's a good idea to test the script in case you encounter any problems. &nbsp;I went to option 9 on the hamvoip menu which is the Bash shell prompt. and ran the script with a radio turned on to see what happened.</p>
<p>Then you can add a function in the [functions stanza located in rpt.conf to call the script. &nbsp;It could look something like this.</p>
<p>83=cmd,/usr/local/sbin/weather_data</p>
<p><br></p>
<p>Once the function is created and files are loaded, go to option 11 on the main menu of the node, which is the asterisk client.</p>
<p>&nbsp;</p>
<p>Type</p>
<p>Rpt reload</p>
<p>&nbsp;</p>
<p>This reloads rpt.conf</p>
<p>&nbsp;</p>
<p>Then, when AutoSky issues a warning, you can press *83 to see what the warning is. &nbsp;If there are no warnings or watches, invoking the script will report no active watches or warnings. &nbsp;</p>
<p>&nbsp;</p>
<p>You can choose any function. &nbsp;I chose *83 since *81 and *82 are time and weather related.&nbsp;</p>
