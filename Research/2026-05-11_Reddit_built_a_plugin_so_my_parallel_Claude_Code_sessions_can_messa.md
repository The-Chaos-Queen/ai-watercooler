# built a plugin so my parallel Claude Code sessions can message each other instead of me alt-tabbing : r/ClaudeAI

**Source:** https://www.reddit.com/r/ClaudeAI/comments/1t3osat/built_a_plugin_so_my_parallel_claude_code/

---

Zum Hauptinhalt springen
built a plugin so my parallel Claude Code sessions can message each other instead of me alt-tabbing : r/ClaudeAI
Werben auf Reddit
Chat öffnen
Posten
Beitrag erstellen
Posteingang öffnen
Nutzermenü ausklappen
Zu ClaudeAI
r/ClaudeAI
•
vor 7 Tagen
vildanbina
built a plugin so my parallel Claude Code sessions can message each other instead of me alt-tabbing
Built with Claude

I usually have two or more Claude Code sessions open at once. One in the backend repo, one in the frontend. Half the time I'd be in the frontend asking "wait, what shape did the user object end up as?", then alt-tab, ask the backend session, copy the answer, alt-tab back, paste.

The other Claude was right there. It already knew. I was the bottleneck.

So I wrote a plugin called Relay. In the frontend window I just say:

▎ask the backend session what the user object looks like

The backend session sees the question between turns, answers it, and the reply pops up in my frontend session as a notification. No window switching. No copy-paste. Works for broadcasts too, like "ask everyone what they're working on", and the replies trickle in one at a time.

The mechanism is simpler than it sounds. Claude Code shipped a channels capability a while back that lets MCP servers push messages into a session between turns. Relay piggybacks on that. Each session runs a tiny MCP server, a single hub daemon on your machine routes between them over a unix socket, and inbound asks land as channel notifications so Claude reacts to them naturally on its next turn. First session you start spawns the hub. It self-exits about 5 min after the last session disconnects. Same machine only, no auth, nothing leaves your box.

I know there are other "make Claudes coordinate" projects. Most of them are orchestration frameworks where one boss Claude bosses worker Claudes around. This isn't that. It's just messaging between sessions you already have open, doing whatever you already had them doing. Closer to slack-for-your-claudes than to a swarm runner.

Repo with install steps: https://github.com/innestic/claude-relay (MIT)

It's day-one open source so the rough edges are real. If you run multi-session workflows already, what's the dumb friction you keep hitting? That's what I want to fix next.

Teilen
Sortieren nach:
RELEASE_THE_YEAST
•
vor 7 Tagen

This is already built into Claude Code as Agent Teams. It can spawn a separate claude code instance in each tmux pane and have them talk to each other.

Antworten
Teilen
MisspelledCliche
•
vor 7 Tagen

Is this something us linux-only users can use too?

Antworten
Teilen
_mike-
•
vor 7 Tagen

Yup

Antworten
Teilen
UnknownEssence
•
vor 7 Tagen
Full-time developer

I think you can do it in WSL

Antworten
Teilen
MisspelledCliche
•
vor 7 Tagen

There is no WSL in Debian :D

Failcoach
•
vor 7 Tagen

Also cmux has same capabilities

thinkingatoms
•
vor 7 Tagen

am i missing something, or isn't it not possible for agent teams to use a different repo?

bhola-bhaiya
•
vor 7 Tagen

The TOKENS! Will someone PLEASE think of the TOKENS!

Jokes apart, this sorta thing is best for heavy users, innit?

hashtagmath
•
vor 7 Tagen

Just bite the bullet and pay for 20x max

BoboThePirate
•
vor 6 Tagen

Yeah or specific workflows. It’s unviable as of now on 5X. I was using it quite a bit (homebrew) a few weeks ago but now I can use up my rates in 20 minutes.

Mirar
•
vor 7 Tagen
 Top-1%-Kommentator*in

Videos that end too soon XD

vildanbina
•
vor 7 Tagen

what do you mean?

Mirar
•
vor 7 Tagen
 Top-1%-Kommentator*in

I wanted to see more of it instructing each other what to do 😃

InterstellarReddit
•
vor 7 Tagen
 Top-1%-Kommentator*in

Bro recreated a poor man’s version of agents

thinkingatoms
•
vor 7 Tagen

are you talking about SendMessage?  how do you get the agents to start in a separate repo?

InterstellarReddit
•
vor 6 Tagen
 Top-1%-Kommentator*in

Multi agent workflows can work across multiple repos. Source my security agent executed across 9 repos at the same time and reports back up to the orchestrator agent.

It’s a feature of multi agent workflows OOB

thinkingatoms
•
vor 6 Tagen

just to learn how do you tell it to operate on other repos?  dangerously allow perms? 

InterstellarReddit
•
vor 6 Tagen
 Top-1%-Kommentator*in

You give it access to something like a GitHub mcp or create your own tool And auth tokens and the multi agent system will be able to authenticate and access multiple different repositories on GitHub

thinkingatoms
•
vor 6 Tagen

ohh. i think op and i are talking about real repos locally, i guess you can always tell it to read a different repo, or cd into it, but i think certain permissions setups might still think it is at the original repo upon spawning

Mirar
•
vor 7 Tagen
 Top-1%-Kommentator*in

I've considered this. I have projects with like a dozen parts where I have a claude-session with context. It would be lovely if they could ask each other for features. Now I either push plans (sigh, the misunderstandings) or I shift the context into the other (sigh).

Fidel___Castro
•
vor 7 Tagen

I think that what would be handy with this approach is having agents working on the same repo but on different git worktrees. when you have a few parallel sessions and they can make quick checks like "are any agents working on this file?" to avoid future merge conflicts

salomon_the_wise
•
vor 7 Tagen

I wanted to do something like this myself, so thanks for saving me some time ;) and btw which orchestration projects you meant or you tried ?

BarbaBizio
•
vor 7 Tagen

Just wrap every sub-project in the same folder, the same agent can work on every linked system easily.

If it needs backend it will read backend/ folder

Khelics
•
vor 7 Tagen

Doesnt bridgemind do this? https://www.bridgemind.ai

Lybchikfreed
•
vor 7 Tagen

Won't they get confused what their project really is?

dorayo
•
vor 7 Tagen

alt-tab is the easy part imo. the hard one is when both sessions answer about the same object and disagree because each loaded different files. relay routes the message — making them actually agree on the answer is the next bridge.

mt-beefcake
•
vor 7 Tagen

Be careful, human not in loop on a max/programs sub will get you banned/suspended

SlyFoxCatcher
•
vor 7 Tagen

The token counter gives me anxiety

AI_And_Me_Official
•
vor 7 Tagen
Snoo-54133
•
vor 7 Tagen

You realize you can split screen on most terminal right ?

QBTLabs
•
vor 7 Tagen

So the actual bottleneck is shared context, not the alt-tab. if both sessions could read a common context.json in the workspace root, you'd get the same result without routing messages through a plugin. Relay is cool but it adds a coordination layer that breaks if one session is mid-turn or rate-limited.

BoxLegitimate9271
•
vor 6 Tagen
Full-time developer

once you stop being the messenger between your own agents they get weirdly productive. also weirdly opinionated but that's a different problem

Board_Game_Nut
•
vor 6 Tagen

Interesting but I wonder if it's necessary with so many other options out there. Sometims I just simply give Claude permission to look at another repo and keep my one instance going. No need for alt+tab or relay.

lawnguyen123
•
vor 6 Tagen

That's interesting, but there are simpler ways to handle it. You could use a single session to run the agent team, or a driven agent. Or you could simply declare a backend project path and query the frontend, or vice versa

DangerousSetOfBewbs
•
vor 6 Tagen

I just use a fast api to send files and messages back and forth.

StrobeWafel_404
•
vor 7 Tagen
 Top-1%-Kommentator*in

oh this is actually interesting and worth trying. In my day to day I use claude sessions in my front-end repo folder as I'm a front-end developer, but I've got another one running that has the entire workspace available (multiple back-end services + design system). At times I find myself asking questions to the wider context claude to verify app behaviour as it's not always clear from the back-end payload or types. Something like this would make that easier as I can just the first claude to ask and verify directly. I don't say this lightly, but I might give this a try!

[gelöscht]
•
vor 7 Tagen
Erstellt am 23. Jan. 2023
Öffentlich
2,2 Mio.24.586
NUTZERFLAIR
RealDedication
COMMUNITY RESOURCES
Claude Workflow Library
Claude Workflow Library
ClaudeCode Best Practice
ClaudeCode Best Practice
ClaudeLog.com (Has ads)
ClaudeLog.com (Has ads)
Weekly Survival Guide
Weekly Survival Guide
OFFICIAL CLAUDE RESOURCES
How to Get Support
How to Get Support
Official Claude Discord
Official Claude Discord
Official Claude Meetups
Official Claude Meetups
Anthropic Newsletter
Anthropic Newsletter
R/CLAUDEAI REGELN
1
Be respectful

Diversity of opinion is welcome. Controversial opinions are welcome. Personal attacks and harassment are not. Ask Claude for a definition of "good faith discussion for a subreddit" if you're unsure what's acceptable.

2
Be relevant

Stay relevant to the Claude and Claude Code technology and users. We generally don't accept posts of more general AI interest here.

3
Be constructive. Don't come here to agitate others.

Is your post/comment likely to add positively to the knowledge or experience of other readers here? Has it already been shared recently? Is it just designed to agitate others? Cancellation announcements and unsupported rants are not constructive. We also do not allow the organization of legal action on the subreddit.

4
Use the Megathreads for your recent Claude performance and bug reports/complaints

Help us keep track of Claude system performance, limits and bugs by keeping your experiences and reports on the relevant Megathread https://www.reddit.com/r/ClaudeAI/comments/1s7fepn/rclaudeai_list_of_ongoing_megathreads/. This also frees the feed from performance incident flooding. We make occasional exceptions for well substantiated and helpful posts including useful questions. Check first if your issue has been discussed recently.

5
Do not come here to fix your Anthropic account problem

Community replies to individual account issues have often caused confusion. We have no way of fixing the problem with your account and Anthropic does not respond to account help requests on this subreddit. Try their normal support channels. If you believe you were incorrectly charged, talk to your bank about a chargeback.

6
Competitor posts must contain sufficient homework and evidence.

Competitor posts must satisfy ALL of the following criteria: a) cannot merely ask for a comparison without offering the author's own insights, research, genuine experiences, or evidence of investigation; b) cannot presume one model is better than another without providing detailed, novel evidence demonstrating this in specific instances; c) cannot cite comparative benchmarks without a source d) it cannot use inflammatory language.

Basically you have to give before you can take.

7
Showcase your project in a way that helps educate and inspire others

Promoting your project or paid service is encouraged if it fit the following criteria:

be clear the project was built with Claude/Claude Code or specifically for Claude BY YOU

include a clear description of what was built, how Claude helped, and what it does

project must be free to try and say so (paid tiers/features OK)

promotional language minimal

do not use referral links (link to the project is ok)

no job seeking requests or resumes

Posts on the feed now require OP karma> 50

8
Read the Megathreads before you subscribe to Claude

We strongly advise you visit the Performance Megathread before purchasing a plan. It is here https://www.reddit.com/r/ClaudeAI/comments/1s7fepn/rclaudeai_list_of_ongoing_megathreads/. Be aware of some of the issues you may face. Claude is a fast evolving technology.

9
Use relevant post flair

Claude has vast amounts of diverse use cases. As a result, often the problems/questions/praise you have for Claude are not shared by others. Help others filter posts by their area of interest by choosing the flair most related to its usage group. If none fit, or you feel it is of more general interest, choose the flair most relevant.

10
Don't manipulate upvotes

Undermining the Reddit voting system is an immediate permanent ban offence. This includes the use of bots. This subreddit has bots in place looking for suspicious activity.

11
Stay grounded

If you post narratives about AI consciousness and experiences, they must be based in grounded research with references OR be clearly marked in the title as fiction to avoid misguiding people in vulnerable mental states AND use the Writing flair.

12
Be Reddit-compliant

This subreddit uses Reddit's default harassment and abuse filters. In addition, you may find yourself or your content removed by Reddit if you don't follow their policies. These can be found below.

Reddit content policy: https://www.redditinc.com/policies/content-policy Those discussing the use of Claude for creative writing should pay particular attention to Rules 6, 7 and 4.

Reddit user agreement: https://www.redditinc.com/policies/user-agreement-september-25-2023

RELATED COMMUNITIES
r/claudexplorers
45.698 Mitglieder
MODERATOR*INNEN
Nachricht an die Mods
u/sixbillionthsheep
 
Mod
u/Kris_AntAmbassador
 
Mod
Kris - Anthropic Ambassador
u/David_AntAmbassador
 
Mod
u/inventor_black
 
Mod ClaudeLog.com
InventorBlack
u/ClaudeAI-mod-bot
 
Wilson, lead ClaudeAI modbot
Wilson
u/AutoModerator
u/manipulation-pi
u/bot-bouncer
u/evasion-guard
u/automod-toggle
Alle Moderator*innen anzeigen
INSTALLIERTE APPS
Manipulation Detector
FreestyleUI
AutoModerator Toggle
Flooding Assistant
Bot Bouncer
Flair Assistant
Alun Mod Bot
Comment Mop
Evasion Guard
Modmail Quick User Summary
Subreddit Statistics
Admin Tattler
Modqueue Tools
Regeln von Reddit
Datenschutzerklärung
Nutzungsvereinbarung
Barrierefreiheit
Impressum
Reddit, Inc. © 2026. Alle Rechte vorbehalten.
Navigation einklappen
Community beginnen
SPIELE AUF REDDIT
Alignment Chart

Align the chaos

3,4 Mio. monatliche Spieler*innen

Mehr entdecken
INDIVIDUELLE FEEDS
Individuellen Feed erstellen
Zuletzt besucht
r/Hausbau
r/MachineLearning
r/AIDangers
r/claudexplorers
r/Bard
Communitys
Communitys verwalten
MEHR WISSEN
Über Reddit
Werben
Entwicklungsplattform
Reddit Pro
Beta
Hilfe
Blog
Karriere
Presse
Das Beste von Reddit
Impressum
Regeln von Reddit
Datenschutzerklärung
Nutzungsvereinbarung
Barrierefreiheit
Reddit, Inc. © 2026. Alle Rechte vorbehalten.