(function () {
    function getMarkdownFromElement(element) {
        if (!element) return "";

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
                } else {
                    md += content;
                }
            }
        });
        return md;
    }



    const AI_PLATFORMS = {
        'claude.ai': {
            name: 'Claude',
            userSelector: '.\\!font-user-message',
            assistantSelector: '.font-claude-response',
            assistantName: 'Claude'
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

    function extractChat() {
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
        document.querySelectorAll('details:not([open])').forEach(d => d.setAttribute('open', ''));
        // Also click any "show thinking" buttons (Claude-specific)
        document.querySelectorAll('[data-testid="thinking-toggle"], button[aria-label*="thinking"], button[aria-label*="Thinking"]').forEach(btn => {
            try { btn.click(); } catch (e) { }
        });
        // Arena/LMSYS specific "Thought for" buttons
        document.querySelectorAll('button').forEach(btn => {
            if (btn.textContent.includes('Thought for') && btn.getAttribute('aria-expanded') === 'false') {
                try { btn.click(); } catch (e) { }
            }
        });
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

                // Claude specific: .standard-markdown
                if (platformKey === 'claude.ai' && role === config.assistantName) {
                    const mdContainer = node.querySelector('.standard-markdown');
                    if (mdContainer) contentNode = mdContainer;
                }
                // Gemini specific: .markdown inner container preferred
                else if (platformKey === 'gemini.google.com') {
                    const mdContainer = node.querySelector('.markdown');
                    if (mdContainer) contentNode = mdContainer;
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

                let text = getMarkdownFromElement(contentNode).trim();

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
            try {
                const markdown = extractChat();
                sendResponse({ status: "success", data: markdown });
            } catch (e) {
                console.error(e);
                sendResponse({ status: "error", message: e.toString() });
            }
        }
        return true;
    });
})();
