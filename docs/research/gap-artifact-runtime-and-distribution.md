STATUS: COMPLETE

# Gap fill: artifact runtime and distribution surfaces

Lane: what each delivery surface can actually do for Robo-Kit (published Claude artifact, claude.ai chat with a plugin or connector, Claude Desktop local server, Claude Code plugin, API-key CLI). Researched 28 Sep 2026 from current Anthropic documentation, the platform-served artifact type definitions (runtime contract 0.2.61), and one live throwaway artifact.

Two items were **not** exercised live, on purpose: the actual Claude call with a page tool, and switching the probe to "Anyone with the link". The first needs the viewer to click a consent dialog that spends their usage; the second makes the page public. Both are documented below from the type definitions and help pages, and the probe page has a button so the owner can run the Claude call in one click.

## 0. Bottom line (plain language)

1. **The artifact chat does run on the viewer's own Claude plan, but for a new artifact almost nobody else can use it.** Anthropic's sharing rules say artifacts that use Claude cannot be shared by public link, and people invited from outside your organization cannot use the Claude parts. On a Pro or Max account that leaves the owner only. On Team or Enterprise it covers members of that one organization. The old "publish a chat artifact, anyone signs in and uses it on their own plan" route exists only for legacy artifacts made before 16 Sep 2026, and new ones can no longer be made.
2. **The page can pick a tier, not a model.** Tiers are `quick`, `default`, `complex`; the platform may downgrade to what the viewer's plan allows and reports the tier that answered. There is no page-controlled system prompt. Multi-turn works because the page keeps the history. **Real tool calling exists** (`options.tools`, up to 16 tools in the live view), so page functions do not have to be emulated with JSON replies, though a JSON fallback is still needed for views that reject tools.
3. **The page cannot fetch outside data.** Live test: Bank of Canada Valet, SEC and even a jsDelivr JSON file were all blocked by the `connect-src` policy. A data file published alongside the page **can** be fetched: a synthetic 7.8 MiB file shaped like the real 7,957-fund universe loaded in about 0.6 s and parsed in about 40 ms.
4. **claude.ai chat users (web, desktop, mobile) can only reach a remote MCP server** that Anthropic's cloud connects to over the public internet. Local stdio servers work only in Claude Code, in Claude Desktop (config file or `.mcpb`), and in Cowork sessions on the desktop. So a Robo-Kit connector for chat users re-serves whatever data it returns; it must return Green data only or compute on inputs the user supplies.
5. **Only the artifact page and an API-key app can check the model's reply before the user sees it.** Claude Code and Cowork can check it just after it is shown (Stop hook) and force a correction. claude.ai chat cannot run hooks at all.

## 1. Sources opened and method

Primary sources (all opened on 28 Sep 2026; raw text saved in the lane scratchpad and grepped for the quotes below):

| Short name | Source |
| --- | --- |
| `sample.d.ts`, `claude.d.ts`, `mcp.d.ts`, `permissions.d.ts` | Platform-served `window.claude` type definitions, runtime contract 0.2.61, extracted by Claude Code 2.1.281 to the local Claude Code skill folder (`artifact-capabilities/0.2.61/`) |
| HC-artifacts | https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them ("Updated this week") |
| HC-share | https://support.claude.com/en/articles/9547008-publish-and-share-artifacts ("Share artifacts", "Updated this week") |
| CC-artifacts | https://code.claude.com/docs/en/artifacts (and `.md`) |
| HC-custom-connectors | https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp (11 Aug 2026) |
| HC-use-connectors | https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities (20 Aug 2026) |
| Docs-remote-mcp | https://claude.com/docs/connectors/custom/remote-mcp |
| Docs-plugins | https://claude.com/docs/plugins/overview |
| Docs-platform | https://claude.com/docs/plugins/platform-support |
| Docs-directory | https://claude.com/docs/directory/publish |
| Directory Policy | https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy (15 Apr 2026) |
| AUP | https://www.anthropic.com/legal/aup (effective 15 Sep 2025) |
| CC-plugins-ref | https://code.claude.com/docs/en/plugins-reference |
| CC-marketplace-ref | https://code.claude.com/docs/en/plugins/marketplace-reference |
| CC-hooks | https://code.claude.com/docs/en/hooks |
| CC-mcp | https://code.claude.com/docs/en/mcp |
| CC-model-config | https://code.claude.com/docs/en/model-config |
| Models | https://platform.claude.com/docs/en/models/overview |
| HC-usage | https://support.claude.com/en/articles/9797557-usage-limit-best-practices |
| Docs-skills | https://claude.com/docs/skills/overview and https://claude.com/docs/skills/how-to |
| Docs-mcp-apps | https://claude.com/docs/connectors/building/mcp-apps/getting-started |
| MCPB repo | https://github.com/modelcontextprotocol/mcpb (via `gh api`: 2,120 stars, pushed 2026-05-26) |
| Blog 2025 | https://claude.com/blog/claude-powered-artifacts (25 Jul 2025; historical, partly superseded) |

## 2. Live probe

**Artifact:** a private probe artifact ("Robo-Kit Runtime Probe", private to the owner, capability `sample` declared, runtime contract 0.2.61). Supporting file `probe-universe.json`: 8,175,865 bytes of **synthetic** data (random values with the same shape as `data/v2/universe.csv`: 7,957 rows x 46 columns, plus 7,792 funds x 120 months of integer basis-point returns). No real or Red-licensed values were published.

Opened in the owner's own signed-in Chrome (desktop, Windows). The built-in browser pane was not signed in and showed "Sign in to view this page", which itself confirms a private artifact needs a signed-in owner.

| Check | Result (verbatim from the page) |
| --- | --- |
| Page origin | `https://<artifact-id>.frame.claudeusercontent.com` (framed) |
| `window.claude` | object; enumerable keys `[]` |
| Legacy `window.claude.complete` | `undefined` |
| `claude.use("sample")` | resolved a function |
| `sample.limits()` | `{"maxPromptBytes":65536,"tools":{"maxCount":16}}` (no `images` member, so image input is unavailable in this view) |
| `permissions.state()` | `{"sample":"prompt"}` (the first call would ask the viewer) |
| fetch Bank of Canada Valet `FXUSDCAD` | `TypeError: Failed to fetch`; CSP event `violatedDirective: connect-src` |
| fetch `https://www.sec.gov/files/company_tickers.json` | `TypeError: Failed to fetch`; `connect-src` |
| fetch `https://cdn.jsdelivr.net/npm/lodash@4.17.21/package.json` (allowlisted script CDN) | `TypeError: Failed to fetch`; `connect-src` |
| fetch `probe-universe.json` (published beside the page) | HTTP 200, 8,175,865 chars, fetch 590 ms / 580 ms, `JSON.parse` 40 ms / 35 ms (two loads), 7,957 rows, 46 columns, 7,792 funds x 120 months |
| Share menu (opened and closed, nothing changed) | General access offered "Only people invited" (selected) and "Anyone with the link"; the "Anyone with the link" option carried no `aria-disabled` flag. Selecting it was not tried. |

Not run: the "Run tool-call test" button (calls `sample()` with one page tool `get_fund_weight` and a tier picker, then prints the reply, `modelTierApplied` and the number of tool calls). Running it needs the owner to accept the consent prompt; it spends a small amount of the owner's usage.

Housekeeping: a second, accidental copy was created while republishing (private, no capabilities, no data file). Both are private throwaways; the owner can delete them from the gallery.

## 3. Capability matrix by surface

Legend: Yes / No / Partly, with the evidence id from section 4.

| Question | A. New published artifact (`sample`) | A0. Legacy chat artifact (made before 16 Sep 2026) | B. claude.ai chat (web, desktop, mobile) + plugin / remote connector | C. Claude Desktop local server (`.mcpb` or config) and Cowork | D. Claude Code plugin (skills + stdio MCP + hooks) | E. API-key CLI or own web app (Messages API) |
| --- | --- | --- | --- | --- | --- | --- |
| Whose plan pays | Viewer's (a1, a2) | Viewer's (a6) | User's own plan | User's own plan | User's own plan or API key | Key holder (per token) |
| Who can use the AI part | Owner; org members on Team/Enterprise. Not public-link viewers, not outside invitees (a3, a4) | Anyone with the link; sign-up asked only for Claude features (a6). No new ones (a7) | Any signed-in user who adds the plugin/connector; Free: 1 custom connector (e1) | Desktop app users signed in to claude.ai (e5) | Claude Code users; artifacts publishing needs Pro+ (a9) | Anyone with a key |
| Viewer without a Claude account | Cannot open (a5); conflicting doc (a8) | Can view; must sign up to use Claude | No | No | No (needs login or key) | Yes (your app) |
| Pick exact model | No; tier only `quick`/`default`/`complex`, may be downgraded (b2) | Not researched | Yes, model picker | Yes | Yes, `/model` (b7) | Yes |
| Page/app-controlled system prompt | No; rules go in a leading user turn (b1) | Not researched | Skill + connector instructions | Same as B | Skill, CLAUDE.md, output style | Yes |
| Multi-turn | Yes, page keeps turns; 64 KiB total (b3, c1) | Not researched | Yes (chat) | Yes | Yes | Yes |
| Tool / function calling | Yes, page functions via `options.tools`; max 16 (live); `tools_unavailable` in some views (b4, b5) | "Limited to a text-based completion API" (2025 blog) | Yes, MCP tools of the connector; skill scripts in code sandbox (e7) | Yes, local MCP tools | Yes, MCP + scripts + hooks | Yes |
| Reach the internet from the tool side | No, page `connect-src` = own origin + Google Fonts (d1, live) | Not researched | Remote connector runs on your server; skill sandbox network not verified | Yes (local process) | Yes (local process) | Yes |
| Bundle 7.5k-fund universe | Yes: separate published file, own-origin fetch (live); page cap 16 MiB (d2) | n/a | Plugin up to 200 MB / 5,000 files (e9) | Yes | Yes | Yes |
| Inspect the reply before the user sees it | **Yes** (page receives text and decides what to render) (f1) | Not researched | **No** (hooks ignored in chat) (f3) | After display only (Cowork loads hooks) (f3) | After display only: Stop hook, can force a correction (f2) | **Yes** |
| Listing channel | Share menu only | Publish link | Anthropic directory (plugin bundle + connector) (e8) | Directory no longer takes `.mcpb` listings (e8) | Own marketplace repo or directory | Your own |

## 4. Findings with verbatim evidence

### (a) Calling Claude from a published artifact, billing and who can use it

- **a1. In-page API.** New artifacts call Claude through `const sample = await claude.use("sample")`, then `sample(input, options)` or `sample.json(...)`. The capability must be declared at publish (`capabilities: {sample: {}}`). `sample.d.ts`: "A call that reaches Claude spends the VIEWER's own Claude usage, so the first call in a view asks the viewer to allow it". The old flat API is gone from new pages: `claude.d.ts` says "(Chat artifacts use a different, flat `window.claude`; neither `use()` nor these namespaces exist there.)" and the live probe found `window.claude.complete` undefined. The exact legacy name `window.claude.complete` is not stated in any Anthropic page I opened (INSUFFICIENT EVIDENCE beyond the 20 GitHub code hits already in prior-art-github.md).
- **a2. Billing, current help page.** HC-artifacts: "People using it sign in with their Claude account and interact with their own instance. No API keys are required, and there's no cost to you."
- **a3. Public link is not allowed for Claude-using artifacts.** HC-share, under "Artifacts that can't be shared outside your organization": "By link: Artifacts that connect to your apps or use Claude can't use "Anyone with the link."" CC-artifacts says the same for connectors: "An artifact that calls connectors can't be shared to a public link on any plan."
- **a4. Outside invitees lose the Claude parts.** HC-share: "People you invite from outside your organization can't invite others or change sharing settings. Parts of the artifact that use Claude or your connectors don't work for them." On Pro and Max every other person is outside your organization, so the AI chat is owner-only there.
- **a5. Account needed to open.** HC-share: "Everyone needs a Claude account. People without one can't open a shared artifact, even with the link. The only exception is a legacy artifact published from a chat."
- **a6. Legacy artifacts were the public route.** HC-share: "Anyone with the link can view and use it without a Claude account. They're asked to sign up only for features that use Claude." and "Features that use Claude count toward their own usage limits."
- **a7. No new legacy artifacts.** HC-artifacts: "Legacy artifacts are artifacts made in a chat before September 16, 2026. They keep working, and you can still publish and share them, but you can't make new ones."
- **a8. Conflict.** CC-artifacts says "**Publicly**: share a link that anyone on the internet can open, with no claude.ai sign-in required. On Pro and Max plans, a public link is the only way to share an artifact." This contradicts a5 (sign-in required) and HC-share's email-invite option for Pro/Max. The live Share menu offered "Anyone with the link" without a disabled flag even though the probe declares `sample`. Treat as unresolved; either way, a signed-out viewer has no plan to bill, so the AI part cannot work for them.
- **a9. Free plan.** Free users can create artifacts in chat (HC-artifacts table) but CC-artifacts: "Artifacts are available on Pro, Max, Team, and Enterprise plans and require a session signed in with `/login`." No page I opened says whether a Free-plan viewer can run `sample`; given a3/a4, a Free viewer cannot reach a Claude-using artifact owned by someone else anyway (inference, not tested).

### (b) Model tier, system prompt, history, tools

- **b1. No system prompt.** `sample.d.ts`: "has no tools except the page functions you pass in `options.tools`, and there is no system prompt the page controls: put the instruction, the page's data and the output format you want in `input`."
- **b2. Tier, not model.** `modelTier` is `"default" | "complex" | "quick"`. `sample.d.ts`: "The platform may serve a nearby cheaper tier when the viewer's plan lacks the one asked for — {@link SampleResult.modelTierApplied} reports which tier actually answered."
- **b3. History.** `sample.d.ts`: "a short conversation the PAGE keeps (Claude keeps nothing between calls), oldest first, that must START and END with a `user` turn."
- **b4. Native tools.** `sample.d.ts`: "every round is a separate paid request on the viewer's account that re-reads everything so far; a call that uses two tools is three requests." Tools are never cached, and `cache` other than `false` with `tools` is rejected.
- **b5. Tools can be missing in a view.** `sample.d.ts`: "Only where {@link limits} reports `tools` — elsewhere the call rejects `tools_unavailable`." The live owner view reported `"tools":{"maxCount":16}`. So emulation with structured JSON is **not required**, but a fallback is: `sample.json()` exists and "the platform also tells Claude the reply will be machine-parsed."
- **b6. Streaming and structured output.** `onText` streams the whole answer so far; `sample.json` parses one JSON value tolerantly and rejects `invalid_json` otherwise.
- **b7. Exact model choice elsewhere.** CC-model-config: "use `/model <alias|name>` to switch immediately". Models: Claude Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 4.5 are current; Haiku 4.5 retirement "Not sooner than October 15, 2026", so an API-key CLI must not hard-code it as the only cheap model.

### (c) Context and rate limits

- **c1. Artifact input cap.** `sample.d.ts`: "Either way the text totals at most 64 KiB (`prompt_too_large` beyond that)". Live: `maxPromptBytes: 65536`. That is roughly 16k tokens for instructions, page data and all turns together, far below the model context window.
- **c2. Tool payloads.** `sample.d.ts`: "Return a string or plain data (JSON-encoded, at most 32 KB)." Tool description at most 1 KB, input schema at most 4 KB, `execute` aborted after 150 s, "The platform allows a handful of rounds and makes the last one an answer."
- **c3. Concurrency.** `sample.d.ts`: "A couple of calls run at once for a viewer, a few more wait their turn, and a flood rejects `rate_limited`." Each round is capped at about five minutes; default-tier first text usually 5-60 s.
- **c4. Plan limits.** HC-usage: "navigate to Settings > Usage to view progress bars showing how much of your five-hour session and weekly usage limits you’ve consumed." Artifact calls draw on these (a2).
- **c5. Model context windows (chat, Claude Code, API).** Models table: "Context window | 1M tokens | 1M tokens | 1M tokens | 200K tokens" for Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 4.5.
- **c6. MCP output in Claude Code.** CC-mcp: "Claude Code displays a warning when MCP tool output exceeds 10,000 tokens and limits output to 25,000 tokens by default."

### (d) Network and bundled data

- **d1. No outside fetch.** CC-artifacts: the CSP "lets `fetch`, XHR, and WebSocket calls reach only the page's own origin and the Google Fonts hosts." `sample.d.ts` adds "The page cannot fetch images from URLs (its network is blocked)". Live: three `connect-src` violations (section 2).
- **d2. Size.** CC-artifacts: "The rendered page must be 16 MiB or smaller." The Artifact publishing tool allows 16 MB per page and per text file and 64 MB per version, and serves supporting files at relative paths. CC-artifacts also says "Relative links do not resolve, because nothing is deployed alongside the page"; the live probe contradicts this for `fetch()` of a published supporting file (HTTP 200).
- **d3. Real sizes (measured by script on the local, Red-licensed data; not published).** `data/v2/universe.csv`: 7,957 rows (US 5,770, CA 2,187; 2,611 eligible), 46 columns. As JSON: 7.94 MB in record form, 4.06 MB in column-split form (0.77 MB gzipped). `close_monthly.pkl`: 485 months x 7,792 funds; the last 120 monthly returns hold 404,385 values = 5.66 MB at 4 decimals or 4.42 MB as integer basis points. Split metadata + 120 months in basis points is about 8.5 MB: under the 16 MB per-file cap, but only as a separate file, not inline in a page that also carries the app.

### (e) MCP servers, plugins, directory

- **e1. Custom remote connector (web and desktop).** HC-custom-connectors: Pro/Max go to Customize > Connectors, "+", "Add custom connector", paste the URL, optionally OAuth details, "Add". Team/Enterprise: an Owner adds it under Organization settings > Connectors, then members "Connect". "Free users are limited to one custom connector."
- **e2. Runs from Anthropic's cloud on every client.** HC-custom-connectors: "This is true across every Claude client, including claude.ai, Claude Desktop, Cowork, and the mobile apps. This means your MCP server must be reachable over the public internet from Anthropic's IP ranges."
- **e3. Mobile.** HC-use-connectors: "Installing connectors on mobile is currently in beta—Claude Desktop and web remain the primary path for custom connectors." and a connector added on web or desktop "will be available to use the next time you log in to your account on Claude for iOS or Android."
- **e4. Auth and transport.** Docs-remote-mcp offers Sign in now / Sign in when needed / "No sign-in : anyone with access to the server URL can use the connector." OAuth client options include Client ID Metadata Document and Dynamic Client Registration; request-header auth is beta. "A URL ending in /sse selects the older SSE transport."
- **e5. Local servers.** HC-custom-connectors: "Local MCP servers configured in Claude Desktop via claude_desktop_config.json are a separate mechanism and do use your local network, but those aren't available in Cowork or claude.ai." Docs-remote-mcp: "A desktop extension is a local MCP server packaged with MCPB (MCP Bundles) that runs on your device inside Claude Desktop." Install: Settings > Extensions, "Drag the .mcpb file onto the page. Claude opens a preview of the extension." MCPB README recommends Node.js and supports `server.type = "uv"` for Python. Claude Code: `claude mcp add --transport stdio <name> -- <command>` (CC-mcp).
- **e6. Plugin components by surface.** Docs-platform table: in Chat, skills load, commands load as skills, agents and hooks are "Ignored", a local MCP server "including `.mcpb` bundles" is "Ignored", and a remote server is listed on the plugin's Connectors tab. Docs-plugins: "A bundled connector marked Runs in each session runs on your computer rather than over the internet. It works in Claude Code and in a Cowork session that runs on your computer in the desktop app, not in chat."
- **e7. Skill scripts in chat.** Docs-skills: skills "run in Claude's code sandbox, so **Code execution and file creation** must be on" (Pro, Max, Team, Enterprise). How-to: scripts run "in chat on claude.ai it's what the code-execution environment provides." Sandbox network access was not verified.
- **e8. Manifest schema.** CC-plugins-ref: "`name` is the only required key." "Save the manifest at `.claude-plugin/plugin.json` under the plugin root. Put every other plugin file at the plugin root, not inside `.claude-plugin/`." Defaults: `skills/<name>/SKILL.md`, `commands/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `bin/`. `userConfig` options can be `sensitive` (stored in the OS credential store) and are referenced as `${user_config.KEY}`; Chat ignores an MCP server whose URL contains such a reference. For `bin/`: "claude.ai and Cowork don't install a plugin that has this directory". CC-marketplace-ref: "`name`, `owner`, and `plugins` are required." in `.claude-plugin/marketplace.json`; reserved marketplace names include "`claude-for-financial-services`, `financial-services-plugins`".
- **e9. Size and install limits.** Docs-platform: "Each plugin can contain up to 5,000 files and 200 MB"; chat/Cowork users add a marketplace from a GitHub (or public GitLab/Bitbucket) repo or upload a `.zip`.
- **e10. Directory.** Docs-directory: "Anyone on a paid Claude plan can submit"; a plugin bundle comes from "A GitHub repository, which must be public before the listing goes live"; a remote server is submitted separately as an MCP connector; "the directory no longer accepts local MCP servers packaged as desktop extensions (MCPB). To distribute a local MCP server through the directory, include it in a plugin bundle."
- **e11. Directory Policy items that bind a finance tool.** 1.A "All Software must comply with our Universal Usage Standards and High-Risk Use Case requirements". 4.A excludes "Software that transfers money, cryptocurrency, or other financial assets, or executes financial transactions on behalf of users." 3.A privacy-policy link for software that collects user data or connects to a remote service. 3.F "Developers must verify that they own or control any API endpoint, domain, or user interface their Software connects to". 5.D OAuth 2.0 for authenticated remote servers; 5.E "MCP servers must provide all applicable annotations for their tools, in particular readOnlyHint , destructiveHint , and title ."; 5.C tool names at most 64 characters; 5.F Streamable HTTP.
- **e12. The AUP high-risk rule for finance.** AUP lists "Finance: Use cases related to financial decisions, including investment advice, loan approvals, and determining financial eligibility or creditworthiness" and requires, for advice to consumers, that "a qualified professional in that field must review the content or decision prior to dissemination or finalization", plus AI disclosure at the start of each session.
- **e13. Artifact connectors and local servers.** HC-artifacts: connecting apps to an artifact is "Available on Pro, Max, Team, and Enterprise plans, on Claude on web and desktop" and "Everyone connects their own apps, even when using a shared or published artifact." `mcp.d.ts` allows `host:<name>` servers on the viewer's device through the Claude app, but "only the Artifact's owner can use host servers for now." (Not tested live.)

### (f) Where Robo-Kit code can check the final reply before the user sees it

- **f1. Artifact page: yes.** The page receives the answer and chooses what to render. `sample.d.ts`: "The same promise resolves at the end with the full text, or rejects with the one error shape." With tools, `text` is "the text of every round, a blank line between rounds." `onText` is optional, so the page can buffer, validate every number against tool results (R7.2), and only then show it.
- **f2. Claude Code and Cowork: after display.** CC-hooks: the Stop hook "Runs when the main Claude Code agent has finished responding." "The `last_assistant_message` field contains the text content of Claude's final response". Returning `"block"` "prevents Claude from stopping", so a validator can force a correction turn, and "Claude Code applies an 8-consecutive-continuation cap". The flawed reply has already been shown. Docs-platform says Cowork loads plugin hooks too (not tested).
- **f3. claude.ai chat: no.** Docs-platform: hooks "Ignored" in Chat. The only levers are tool outputs, skill instructions, and MCP Apps. Docs-mcp-apps: "An MCP App is interactive UI that your MCP server renders inside a Claude conversation, such as an interactive chart or map." Numbers drawn by a Robo-Kit MCP App are rendered by Robo-Kit code, not by the model.
- **f4. API-key CLI or own web app: yes**, full control of the Messages API response before display (standard; not re-researched here).

## 5. Contradictions to track

1. Sign-in for public links: CC-artifacts ("no claude.ai sign-in required") vs HC-share ("Everyone needs a Claude account"). Both pages are current.
2. Pro/Max sharing: CC-artifacts ("a public link is the only way to share") vs HC-share (email invitations in beta on Pro and Max).
3. Claude-using artifacts and public links: HC-share says not allowed; the live Share menu still offered the option. Untested whether selecting it is blocked, strips the capability, or works with the Claude part disabled.
4. Supporting files: CC-artifacts says relative links do not resolve; the live probe fetched a published supporting file by relative URL.
5. The July 2025 blog says AI artifacts are "available in beta to Free, Pro, and Max plan users" with "No external API calls (yet)" and "Limited to a text-based completion API". Tool calling and the 16 Sep 2026 legacy cut-off supersede it; do not cite it as current.

## 6. Implications for PLAN_V2 (build, borrow, avoid, disclose)

1. **Rewrite P5's premise.** The public web artifact cannot be the place where "anyone chats with Robo-Kit on their own plan". Make the AI-free guided flow (deterministic JS engine plus templated explanations) the primary public experience, and treat the in-page Claude chat as a feature for the owner and for Team/Enterprise org members. State this in the README and the grant pitch; the current PLAN_V2 row "Claude runs the conversation on the viewer's own Claude plan" overstates reach.
2. **Distribution pattern for everyone else: "publish your own copy".** Ship the page source inside the plugin with a skill that asks the user's own Claude Code to publish it as the user's private artifact. The user is then the owner, the chat works, and it bills their plan. Needs Pro or above and a claude.ai login (a9). Legacy-style one-link distribution is no longer available (a7).
3. **Design the in-page agent for a 64 KiB budget.** No system prompt: `AGENT.md` for the artifact must be a compact rules block (target 8-12 KB) sent as the first user turn every call, plus a rolling window of turns. Keep page state out of the prompt where a tool can return it on demand. Use `cache: false` for chat turns and never call on load.
4. **Use native page tools, keep a fallback.** Expose at most about 10 small tools (profile, screen, optimize, explain_weight, backtest_summary, data_asof), each returning at most 32 KB of plain data with source and as-of fields. Branch on `tools_unavailable` to a `sample.json` path, and on `not_granted` / null to the no-AI flow.
5. **Offer a tier picker, show the tier that answered.** Map UI labels to `quick` / `default` / `complex` and display `modelTierApplied` when it differs. This satisfies R7.4 logging. Exact model choice exists only in chat, Claude Code and the API-key CLI; say so.
6. **Put the R7.2 validator in the page and in the CLI.** In the artifact, buffer the reply (or stream into a hidden buffer), extract every number, check it against the tool results of that call, then render or replace with a templated sentence. In Claude Code and Cowork, add a Stop hook that runs the same checker on `last_assistant_message` and blocks with a correction reason; disclose that a correction may follow a shown reply. In claude.ai chat, R7.2 can only be enforced offline (evaluation harness over the API) plus MCP Apps for figures; the regulation note should say runtime enforcement differs by surface.
7. **Data in the artifact is a bundled, dated snapshot.** Fetching BoC Valet or SEC from the page is blocked, so the build job must pull Green series and publish them as a separate `universe.json` next to the page (own-origin fetch worked at 7.8 MiB). Split metadata from returns, use integer basis points, and keep each file under 16 MB. The existing `universe.csv` mixes Red-derived columns (TMX, Yahoo), so the artifact bundle needs its own Green-only build, enforced by the catalog check in data-sources.md.
8. **claude.ai chat users need either a hosted Green-only connector or skill scripts.** Option A: a Robo-Kit-owned remote MCP server (Streamable HTTP, `readOnlyHint` on every tool, no auth or OAuth 2.0) that serves only Green data and computes on user inputs. Option B: skill scripts plus a bundled Green snapshot running in the claude.ai code sandbox (Pro+, code execution on; network not verified). Never proxy Red sources from a hosted server (licence, and Directory Policy 3.F).
9. **Bring-your-own-data stays local.** The stdio MCP server (Red sources fetched under the user's own access) works in Claude Code, Claude Desktop and desktop Cowork only. Package it in the plugin's `.mcp.json` (Python via `uvx`, or a Node or `uv`-type MCPB bundle). Do not plan a standalone `.mcpb` directory listing; the directory no longer accepts them.
10. **Plugin layout to build now.** `.claude-plugin/plugin.json` (`name: "robo-kit"`, version, description, author, license), `skills/robo-kit/SKILL.md` (the plain-language AGENT rules), `skills/robo-kit/scripts/` (deterministic CLI entry points), `.mcp.json` (local stdio server), optional `hooks/hooks.json` (Stop-hook validator), `userConfig` for an optional data-provider key marked `sensitive`. No top-level `bin/`, or chat and Cowork will refuse the plugin. Marketplace name must avoid the reserved `financial-services-plugins` / `claude-for-financial-services`.
11. **Directory listing is gated by the finance rules, not the code.** Robo-Kit never moves money (4.A is fine), but 1.A imports the AUP high-risk requirements: personalised investment advice to consumers needs qualified human review before it is shown, plus AI disclosure each session. A listed version must stay impersonal and educational (asset-class illustrations, as regulation.md already proposes) or obtain written permission; this also answers regulation.md open question 5 for the directory path. Prepare the listing items: privacy policy, support contact, test account, three example prompts.
12. **Optional owner-only power mode.** An owner-only artifact could call the local Robo-Kit server through `host:robokit` in the Claude desktop app (e13), giving live local data in the page without re-serving it. Untested; low priority.

## 7. Gaps

- The `sample()` call with a page tool was not run live (needs owner consent and usage). Tool round-trip, latency by tier and `modelTierApplied` substitution are documented but not observed. The probe's button runs this in one click.
- Whether selecting "Anyone with the link" on a `sample`-declaring artifact is blocked, and what a signed-out or outside viewer then sees, is untested (changing sharing was out of scope).
- Artifact behaviour inside the iOS/Android apps and the Claude desktop app, and on a phone for the 7.8 MiB load, was not tested; timings above are from one desktop Chrome session.
- Network access from the claude.ai skill code sandbox was not verified.
- Anthropic docs disagree on public-link sign-in and Pro/Max sharing options (section 5).
- No Anthropic page states whether a Free-plan viewer can run `sample` in someone else's artifact.
- Whether the AUP high-risk requirements bind a user-run artifact or plugin billed to the user's own plan (rather than a Robo-Kit-operated service) needs Anthropic or counsel confirmation.
