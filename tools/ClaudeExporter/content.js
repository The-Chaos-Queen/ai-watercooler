(function () {
    const BLOCK_TAGS = new Set([
        'article', 'blockquote', 'details', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'li', 'p', 'section', 'summary'
    ]);

    const STRIP_TAGS = new Set([
        'button', 'input', 'label', 'noscript', 'script', 'style', 'svg', 'textarea'
    ]);

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function normalizeMarkdown(text) {
        return text
            .replace(/\u00a0/g, ' ')
            .replace(/[ \t]+\n/g, '\n')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    function getControlLabel(element) {
        return [
            element?.textContent || '',
            element?.getAttribute?.('aria-label') || '',
            element?.getAttribute?.('title') || ''
        ].join(' ').toLowerCase();
    }

    function shouldPreserveClaudeControl(element) {
        const label = getControlLabel(element);
        return /(show less|show more|thinking|thought for|reasoning|\bdone\b)/i.test(label);
    }

    function isClaudeActionControl(element) {
        const label = getControlLabel(element);
        return /(copy|edit|retry|regenerate|share|download|artifact|menu|options|thumb|good response|bad response|model|branch|quote)/i.test(label);
    }

    function getVisibleAssistantRoots(selector) {
        return Array.from(document.querySelectorAll(selector)).filter(node => !isHiddenElement(node));
    }

    function clickIfExpandable(control) {
        if (!control || isHiddenElement(control)) return false;
        if (isClaudeActionControl(control)) return false;

        const label = getControlLabel(control);
        const ariaExpanded = control.getAttribute('aria-expanded');
        const text = normalizeMarkdown(control.textContent || '');

        const shouldExpand = (
            /show more/i.test(label) ||
            /show more/i.test(text) ||
            ariaExpanded === 'false'
        );

        if (!shouldExpand) return false;

        try {
            control.click();
            return true;
        } catch (e) {
            return false;
        }
    }

    function isHiddenElement(element) {
        if (!element || !element.tagName) return false;
        if (element.hidden) return true;
        if (element.getAttribute('aria-hidden') === 'true') return true;
        if (element.getAttribute('hidden') !== null) return true;
        return false;
    }

    function getClaudeContentNode(node) {
        const markdownNodes = node.querySelectorAll('.standard-markdown');
        const hasThinking = (
            markdownNodes.length > 1 ||
            node.querySelector('details, [data-testid*="thinking"], [data-testid*="reasoning"]') ||
            Array.from(node.querySelectorAll('button')).some(shouldPreserveClaudeControl)
        );

        if (hasThinking) {
            return node;
        }

        return markdownNodes[0] || node;
    }

    function prepareContentNode(node, platformKey, role, config) {
        if (platformKey === 'claude.ai' && role === config.assistantName) {
            const clone = node.cloneNode(true);
            clone.querySelectorAll('details:not([open])').forEach(details => details.setAttribute('open', ''));
            clone.querySelectorAll(Array.from(STRIP_TAGS).join(',')).forEach(element => {
                if (element.tagName === 'BUTTON' && shouldPreserveClaudeControl(element)) {
                    return;
                }
                element.remove();
            });
            clone.querySelectorAll('[aria-hidden="true"]').forEach(element => element.remove());
            return getClaudeContentNode(clone);
        }

        return node;
    }

    async function expandClaudeSections(config) {
        const assistantRoots = getVisibleAssistantRoots(config.assistantSelector);
        let passChanged = false;

        assistantRoots.forEach(root => {
            root.querySelectorAll('details:not([open])').forEach(details => {
                details.setAttribute('open', '');
                passChanged = true;
            });

            root.querySelectorAll('button, [role="button"], summary').forEach(control => {
                if (clickIfExpandable(control)) {
                    passChanged = true;
                }
            });
        });

        return passChanged;
    }

    async function expandGenericSections() {
        let changed = false;

        document.querySelectorAll('details:not([open])').forEach(details => {
            details.setAttribute('open', '');
            changed = true;
        });

        document.querySelectorAll('button, [role="button"]').forEach(control => {
            const label = getControlLabel(control);
            const ariaExpanded = control.getAttribute('aria-expanded');
            const shouldExpand = (
                /(show more|show thinking|thought for|expand reasoning|expand thinking)/i.test(label) ||
                (/(thinking|reasoning)/i.test(label) && ariaExpanded === 'false')
            );

            if (!shouldExpand) return;

            try {
                control.click();
                changed = true;
            } catch (e) { }
        });

        // Kimi: expand collapsed thinking blocks by clicking .toolcall-title-container
        document.querySelectorAll('.container-block .resize-container').forEach(rc => {
            const height = window.getComputedStyle(rc).height;
            if (height === '0px' || parseInt(height) < 10) {
                const block = rc.closest('.container-block');
                const titleClick = block ? block.querySelector('.toolcall-title-container') : null;
                if (titleClick) {
                    try {
                        titleClick.click();
                        changed = true;
                    } catch (e) { }
                }
            }
        });

        // Kimi: open reference sidebar to make sources accessible
        document.querySelectorAll('.ref-action').forEach(refBtn => {
            try {
                refBtn.click();
                changed = true;
            } catch (e) { }
        });

        return changed;
    }

    async function expandCollapsibleSections(platformKey, config) {
        const maxPasses = 8;

        for (let pass = 0; pass < maxPasses; pass++) {
            const changed = platformKey === 'claude.ai'
                ? await expandClaudeSections(config)
                : await expandGenericSections();

            if (!changed) {
                return;
            }

            await sleep(350);
        }
    }

    function getMarkdownFromElement(element) {
        if (!element) return "";
        if (element.nodeType === Node.ELEMENT_NODE && (isHiddenElement(element) || shouldSkipElement(element))) {
            return "";
        }

        let md = "";

        // Special Handling for Code Blocks (Claude specific structures)
        // Check if this element ITSELF is a code block wrapper
        if (element.classList && (element.classList.contains('code-block__code') || element.tagName === 'PRE')) {
            return `\n\`\`\`\n${element.textContent}\n\`\`\`\n\n`;
        }

        // Handle Arena/LMSYS "Thinking" blocks
        // Structure: <div class="not-prose"> <button>Thought for...</button> <div>...content...</div> </div>
        if (element.classList && element.classList.contains('not-prose')) {
            const button = element.querySelector('button');
            if (button && button.textContent.includes('Thought for')) {
                const contentDiv = element.querySelector('div[class*="font-mono"]');
                if (contentDiv) {
                    let thoughtText = contentDiv.textContent.trim();
                    return `> **Thinking Process:**\n> ${thoughtText.replace(/\n/g, '\n> ')}\n\n`;
                }
            }
        }

        // Handle child nodes
        element.childNodes.forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                md += node.textContent;
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (isHiddenElement(node) || shouldSkipElement(node)) {
                    return;
                }

                const tagName = node.tagName.toLowerCase();

                // Recurse first to get content
                let content = getMarkdownFromElement(node);

                if (tagName === 'p') {
                    md += content + "\n\n";
                } else if (tagName === 'br') {
                    md += "\n";
                } else if (tagName === 'strong' || tagName === 'b') {
                    md += `**${content}**`;
                } else if (tagName === 'em' || tagName === 'i') {
                    md += `*${content}*`;
                } else if (tagName === 'code') {
                    // Inline code (if parent is not PRE/CodeStructure)
                    // If it's a code block, the parent check above likely caught it, 
                    // but if this is an isolated code tag:
                    md += `\`${node.textContent}\``;
                } else if (tagName === 'ul') {
                    // List items are handled in recursion, but we need structure
                    // We need to re-process children for LIs specifically to add bullets
                    let listMd = "";
                    node.querySelectorAll(':scope > li').forEach(li => {
                        listMd += `- ${getMarkdownFromElement(li).trim()}\n`;
                    });
                    md += listMd + "\n";
                    return; // Skip standard recursion since we handled children
                } else if (tagName === 'ol') {
                    let listMd = "";
                    node.querySelectorAll(':scope > li').forEach((li, index) => {
                        listMd += `${index + 1}. ${getMarkdownFromElement(li).trim()}\n`;
                    });
                    md += listMd + "\n";
                    return;
                } else if (tagName === 'hr') {
                    md += "\n---\n\n";
                } else if (tagName === 'a') {
                    const href = node.getAttribute('href');
                    const linkText = content.trim() || href || '';
                    md += href ? `[${linkText}](${href})` : linkText;
                } else if (BLOCK_TAGS.has(tagName)) {
                    if (content.trim()) {
                        md += content + "\n\n";
                    }
                } else {
                    md += content;
                }
            }
        });
        return normalizeMarkdown(md);
    }

    function shouldSkipElement(element) {
        if (!element || !element.tagName) return false;
        const tagName = element.tagName.toLowerCase();

        if (STRIP_TAGS.has(tagName)) {
            if (tagName === 'button' && shouldPreserveClaudeControl(element)) {
                return false;
            }
            return true;
        }

        return false;
    }



    const AI_PLATFORMS = {
        'claude.ai': {
            name: 'Claude',
            userSelector: '.\\!font-user-message',
            assistantSelector: '.font-claude-response',
            assistantName: 'Claude'
        },
        'chatgpt.com': {
            name: 'ChatGPT',
            userSelector: '[data-message-author-role="user"]',
            assistantSelector: '[data-message-author-role="assistant"]',
            assistantName: 'ChatGPT'
        },
        'chat.openai.com': {
            name: 'ChatGPT',
            userSelector: '[data-message-author-role="user"]',
            assistantSelector: '[data-message-author-role="assistant"]',
            assistantName: 'ChatGPT'
        },
        'kimi.moonshot.cn': {
            name: 'Kimi',
            userSelector: '.chat-content-item-user',
            assistantSelector: '.chat-content-item-assistant',
            assistantName: 'Kimi'
        },
        'kimi.com': {
            name: 'Kimi',
            userSelector: '.chat-content-item-user',
            assistantSelector: '.chat-content-item-assistant',
            assistantName: 'Kimi'
        },
        'chat.mistral.ai': {
            name: 'Mistral',
            userSelector: '[data-message-author-role="user"]',
            assistantSelector: '[data-message-author-role="assistant"]',
            assistantName: 'Mistral'
        },
        'grok.com': {
            name: 'Grok',
            userSelector: '.items-end > .message-bubble',
            assistantSelector: '.items-start > .message-bubble',
            assistantName: 'Grok'
        },
        'gemini.google.com': {
            name: 'Gemini',
            userSelector: '[class*="query-container"]',
            assistantSelector: '[class*="response-container"]',
            assistantName: 'Gemini'
        },
        'chat.deepseek.com': {
            name: 'DeepSeek',
            userSelector: '.ds-message:nth-child(2)',
            assistantSelector: '.ds-message:nth-child(3)',
            assistantName: 'DeepSeek'
        },
        'lmsys.org': {
            name: 'LMArena',
            userSelector: '.bg-surface-raised',
            assistantSelector: '.bg-surface-primary:not(body)',
            assistantName: 'LMArena',
            reverse: true
        },
        'arena.ai': {
            name: 'LMArena',
            userSelector: '.bg-surface-raised',
            assistantSelector: '.bg-surface-primary:not(body)',
            assistantName: 'LMArena',
            reverse: true
        }
    };

    async function extractChat() {
        // Detect Platform
        const hostname = window.location.hostname;
        // Simple substring match for config keys
        const platformKey = Object.keys(AI_PLATFORMS).find(key => hostname.includes(key));

        if (!platformKey) {
            return `# Chat Export\n\n> **Error**: Unsupported platform (${hostname}).`;
        }

        const config = AI_PLATFORMS[platformKey];
        const messages = [];

        // AUTO-EXPAND: Open all collapsed thinking blocks before extraction
        // Claude uses <details> for thinking, other platforms may use similar patterns
        await expandCollapsibleSections(platformKey, config);
        console.log('[AIExporter] Expanded all collapsed sections.');

        // Select all potential messages
        // We select both selectors
        const selector = `${config.userSelector}, ${config.assistantSelector}`;
        const rawNodes = Array.from(document.querySelectorAll(selector));

        // DEDUPLICATION STEP 1: Hierarchy
        // If Node A contains Node B, and both are selected, usually Node B is a sub-element.
        // We only want the top-most container to avoid reading the same text twice.
        const nodes = rawNodes.filter((node, index, self) => {
            // Check if this node is inside any OTHER node in the list
            const isInsideOther = self.some(other => other !== node && other.contains(node));
            return !isInsideOther;
        });

        console.log(`[AIExporter] Detected ${config.name}. Found ${rawNodes.length} raw nodes -> ${nodes.length} unique top-level nodes.`);

        if (nodes.length > 0) {
            nodes.forEach((node) => {
                let role = "Unknown";

                // Check against selectors. 
                // Note: checking matches() is safer than classList for complex selectors like [data-attr] or >
                if (node.matches(config.userSelector) || node.querySelector(config.userSelector)) {
                    role = "User";
                } else if (node.matches(config.assistantSelector) || node.querySelector(config.assistantSelector)) {
                    role = config.assistantName;
                }

                // Content Node Selection Logic
                let contentNode = node;

                // Claude specific: use the full assistant container when thinking blocks exist
                if (platformKey === 'claude.ai' && role === config.assistantName) {
                    contentNode = prepareContentNode(node, platformKey, role, config);
                }
                // ChatGPT specific: .markdown inner container preferred
                else if (platformKey === 'chatgpt.com' || platformKey === 'chat.openai.com') {
                    const mdContainer = node.querySelector('.markdown');
                    if (mdContainer) contentNode = mdContainer;
                }
                // Gemini specific: .markdown inner container preferred
                else if (platformKey === 'gemini.google.com') {
                    const mdContainer = node.querySelector('.markdown');
                    if (mdContainer) contentNode = mdContainer;
                }
                // Kimi specific: separate thinking (.container-block) from response (.markdown-container)
                // Structure: .segment-content-box > .container-block(thinking) + .markdown-container(response)
                // The response .markdown is a direct child of .segment-content-box > .markdown-container,
                // distinct from the thinking .markdown inside .container-block > ... > .toolcall-content-text
                else if (platformKey === 'kimi.com' || platformKey === 'kimi.moonshot.cn') {
                    const box = node.querySelector('.segment-content-box');
                    if (box) {
                        // Walk all direct children in order: container-block (thinking/search)
                        // and markdown-container (response) can alternate multiple times
                        let combined = '';
                        Array.from(box.children).forEach(child => {
                            if (child.classList.contains('container-block')) {
                                // Thinking or search block — render as blockquote
                                const title = child.querySelector('.toolcall-title-name');
                                const body = child.querySelector('.markdown');
                                const titleText = title ? title.textContent.trim() : 'Thinking';
                                const bodyText = body ? normalizeMarkdown(getMarkdownFromElement(body)) : '';
                                combined += `> **${titleText}**\n`;
                                if (bodyText) {
                                    combined += `> ${bodyText.replace(/\n/g, '\n> ')}\n`;
                                }
                                combined += '\n';
                            } else if (child.classList.contains('markdown-container')) {
                                // Response block — render as normal text
                                const md = child.querySelector('.markdown');
                                if (md) {
                                    combined += normalizeMarkdown(getMarkdownFromElement(md)) + '\n\n';
                                }
                            }
                        });
                        // Collect sources from the reference sidebar (.site-item links)
                        const sourceItems = document.querySelectorAll('a.site-item[href]');
                        if (sourceItems.length > 0) {
                            combined += '\n\n### Sources\n\n';
                            sourceItems.forEach((item, idx) => {
                                const title = (item.querySelector('.site-title') || {}).textContent || '';
                                const site = (item.querySelector('.site-name') || {}).textContent || '';
                                const href = item.href || '';
                                const label = title.trim() || site.trim() || href;
                                combined += `${idx + 1}. [${label}](${href})`;
                                if (site && title) combined += ` (${site.trim()})`;
                                combined += '\n';
                            });
                        }

                        if (combined.trim()) {
                            node._kimiFullContent = normalizeMarkdown(combined);
                        }
                    }
                }
                // LMArena specific: .prose container limits us (excludes thinking), .no-scrollbar includes both
                // Structure: header(.sticky) + content(.no-scrollbar > .not-prose(thought) + .prose(response))
                else if (platformKey.includes('lmsys.org') || platformKey.includes('arena.ai')) {
                    const scrollContainer = node.querySelector('.no-scrollbar');
                    if (scrollContainer) {
                        contentNode = scrollContainer;
                    } else {
                        // Fallback to prose if structure changes, though this might miss thoughts
                        const mdContainer = node.querySelector('.prose');
                        if (mdContainer) contentNode = mdContainer;
                    }
                }

                let text = normalizeMarkdown(getMarkdownFromElement(contentNode));

                // Kimi: use pre-built full content (thinking + response blocks in order)
                if (node._kimiFullContent) {
                    text = node._kimiFullContent;
                }

                // DEDUPLICATION STEP 2: Sequential Content
                // If this message is identical to the previous one, skip it.
                // This handles cases where UI renders shadow copies or accessibility duplicates.
                if (messages.length > 0) {
                    const last = messages[messages.length - 1];
                    if (last.role === role && last.content === text) {
                        return; // Skip duplicate
                    }
                }

                if (text) {
                    messages.push({ role: role, content: text });
                }
            });
        }

        if (messages.length === 0) {
            return `# Chat Export\n\n> **Error**: No messages found for ${config.name}.\n\nDebug Info:\n- Selectors: ${selector}\n- URL: ${window.location.href}`;
        }

        // Apply Reversal if Configured
        if (config.reverse) {
            messages.reverse();
        }

        let output = `# ${config.name} Chat Export\n\n`;
        messages.forEach((msg) => {
            output += `## ${msg.role}\n\n${msg.content}\n\n---\n\n`;
        });

        return output;
    }

    // Listen for messages from Popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === "get_chat") {
            (async () => {
                try {
                    const markdown = await extractChat();
                    sendResponse({ status: "success", data: markdown });
                } catch (e) {
                    console.error(e);
                    sendResponse({ status: "error", message: e.toString() });
                }
            })();
        }
        return true;
    });
})();
