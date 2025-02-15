// 全局状态管理
let currentConversationId = null;
let isSearchEnabled = false;

// 调试工具
const DEBUG = {
    enabled: true,
    log: function(type, ...args) {
        if (!this.enabled) return;
        console.log(`[${type}]`, ...args);
    },
    error: function(type, ...args) {
        if (!this.enabled) return;
        console.error(`[${type}]`, ...args);
    }
};

// DOM 元素缓存
const elements = {
    messageInput: document.getElementById('userInput'),
    sendButton: document.getElementById('askAssistant'),
    responseContainer: document.getElementById('assistantResponse'),
    fileInput: document.getElementById('fileInput'),
    uploadButton: document.getElementById('uploadButton'),
    searchToggle: document.getElementById('searchToggle'),
    searchStatus: document.getElementById('searchStatus'),
    newChatButton: document.getElementById('newChat'),
    conversationsList: document.getElementById('conversationsList')
};

// 初始化时检查所有DOM元素
Object.entries(elements).forEach(([key, element]) => {
    if (!element) {
        DEBUG.error('Init', `DOM元素未找到: ${key}`);
    }
});

// 调试信息
console.log('DOM Elements initialized:', {
    messageInput: !!elements.messageInput,
    sendButton: !!elements.sendButton,
    responseContainer: !!elements.responseContainer,
    fileInput: !!elements.fileInput,
    searchToggle: !!elements.searchToggle
});

// 初始化 markdown-it
const md = window.markdownit({
    highlight: function (str, lang) {
        if (lang && Prism.languages[lang]) {
            try {
                return `<pre class="language-${lang}"><code>${Prism.highlight(str, Prism.languages[lang], lang)}</code></pre>`;
            } catch (__) {}
        }
        return `<pre class="language-none"><code>${md.utils.escapeHtml(str)}</code></pre>`;
    }
});

// 消息状态管理
const ChatState = {
    isStreaming: false,
    currentMessageDiv: null,
    history: [],
    maxHistoryLength: 50,

    createMessageElement(content, role = 'assistant') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        // 创建头像和名称容器
        const avatarNameContainer = document.createElement('div');
        avatarNameContainer.className = 'avatar-name-container';
        
        // 创建头像
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        const img = document.createElement('img');
        img.src = role === 'assistant' ? '/static/image/deepseek.jpg' : '/static/image/user.jpg';
        img.alt = role === 'assistant' ? 'AI' : 'User';
        img.onerror = function(e) {
            console.error(`Error loading image for ${role}:`, e);
            // 加载失败时显示备用图标
            this.style.display = 'none';
            avatar.innerHTML = role === 'assistant' ? '<i class="fas fa-robot"></i>' : '<i class="fas fa-user"></i>';
        };
        avatar.appendChild(img);
        
        // 创建名称
        const name = document.createElement('div');
        name.className = 'name';
        name.textContent = role === 'assistant' ? 'AI助手' : '你';
        
        avatarNameContainer.appendChild(avatar);
        avatarNameContainer.appendChild(name);
        
        // 创建消息内容容器
        const contentContainer = document.createElement('div');
        contentContainer.className = 'message-content';
        
        // 如果是助手消息，添加思维链容器
        if (role === 'assistant') {
            const reasoningDiv = document.createElement('div');
            reasoningDiv.className = 'reasoning-content';
            contentContainer.appendChild(reasoningDiv);
        }
        
        // 添加消息内容
        const messageContent = document.createElement('div');
        messageContent.className = 'content';
        messageContent.innerHTML = role === 'user' ? content : md.render(content || '');
        contentContainer.appendChild(messageContent);
        
        messageDiv.appendChild(avatarNameContainer);
        messageDiv.appendChild(contentContainer);
        
        return messageDiv;
    },

    addTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        this.currentMessageDiv = this.createMessageElement('');
        elements.responseContainer.appendChild(this.currentMessageDiv);
        const contentDiv = this.currentMessageDiv.querySelector('.content');
        if (contentDiv) {
            contentDiv.appendChild(typingDiv);
        }
        elements.responseContainer.scrollTop = elements.responseContainer.scrollHeight;
    },

    updateContent(content) {
        if (this.currentMessageDiv) {
            const contentDiv = this.currentMessageDiv.querySelector('.content');
            if (contentDiv) {
                contentDiv.innerHTML = md.render(content);
                elements.responseContainer.scrollTop = elements.responseContainer.scrollHeight;
            }
        }
    },

    removeTypingIndicator() {
        const typingIndicator = document.querySelector('.typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
};

// 消息渲染
function appendMessage(content, role) {
    if (!content) return null;
    
    const messageDiv = ChatState.createMessageElement(content, role);
    elements.responseContainer.appendChild(messageDiv);
    elements.responseContainer.scrollTop = elements.responseContainer.scrollHeight;
    return messageDiv;
}

// 事件监听器设置
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    if (elements.messageInput) {
        elements.messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                const message = elements.messageInput.value.trim();
                if (message) {
                    handleUserMessage(message);
                }
            }
        });

        elements.messageInput.addEventListener('input', (event) => {
            const charCounter = document.querySelector('.char-counter');
            if (charCounter) {
                const length = event.target.value.length;
                charCounter.textContent = `${length}/8000`;
            }
        });
    }

    if (elements.sendButton) {
        elements.sendButton.addEventListener('click', () => {
            const message = elements.messageInput.value.trim();
            if (message) {
                handleUserMessage(message);
            }
        });
    }

    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', (e) => {
            console.log('File selected');
            handleFileSelection(e);
        });
    }
    
    if (elements.uploadButton) {
        elements.uploadButton.addEventListener('click', () => {
            console.log('Upload button clicked');
            elements.fileInput.click();
        });
    }
    
    if (elements.searchToggle) {
        elements.searchToggle.addEventListener('change', (e) => {
            console.log('Search toggle changed:', e.target.checked);
            toggleSearch(e);
        });
    }
    
    if (elements.newChatButton) {
        elements.newChatButton.addEventListener('click', () => {
            console.log('New chat button clicked');
            createNewConversation();
        });
    }
}

// 用户输入处理
async function handleUserMessage(message) {
    if (!message) {
        showError('请输入消息');
        return;
    }

    if (ChatState.isStreaming) {
        showError('请等待当前回复完成');
        return;
    }

    try {
        // 如果没有当前对话ID，创建新对话
        if (!currentConversationId) {
            const response = await fetch('/conversations', {
                method: 'GET'
            });
            if (!response.ok) throw new Error('Failed to create conversation');
            const conversations = await response.json();
            if (conversations && conversations.length > 0) {
                // 使用最新的对话
                currentConversationId = conversations[0].id;
            } else {
                // 如果没有对话，创建新对话
                const newConv = await createNewConversation();
                currentConversationId = newConv.id;
            }
        }

        ChatState.isStreaming = true;
        elements.sendButton.disabled = true;
        
        // 显示用户消息
        appendMessage(message, 'user');
        ChatState.history.push({ content: message, role: 'user' });
        
        // 显示加载状态
        ChatState.addTypingIndicator();
        
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                conversation_id: currentConversationId,
                search_enabled: isSearchEnabled
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        await handleStream(response);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
        ChatState.removeTypingIndicator();
    } finally {
        ChatState.isStreaming = false;
        elements.sendButton.disabled = false;
    }
}

// 处理流式响应
function handleStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let accumulatedContent = '';

    return new ReadableStream({
        async start(controller) {
            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') continue;

                            try {
                                const parsed = JSON.parse(data);
                                switch (parsed.type) {
                                    case 'content':
                                        accumulatedContent = parsed.content;
                                        ChatState.updateContent(accumulatedContent);
                                        break;
                                    case 'reasoning':
                                        if (ChatState.currentMessageDiv) {
                                            const reasoningDiv = ChatState.currentMessageDiv.querySelector('.reasoning-content');
                                            if (reasoningDiv) {
                                                reasoningDiv.innerHTML = md.render(parsed.content);
                                            }
                                        }
                                        break;
                                    case 'error':
                                        showError(parsed.content);
                                        break;
                                    case 'done':
                                        ChatState.history.push({ 
                                            content: accumulatedContent, 
                                            role: 'assistant'
                                        });
                                        ChatState.removeTypingIndicator();
                                        break;
                                }
                            } catch (e) {
                                console.error('Error parsing SSE data:', e);
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Stream reading error:', error);
                controller.error(error);
            } finally {
                controller.close();
                reader.releaseLock();
            }
        }
    });
}

// 文件处理
function handleFileSelection() {
    const file = elements.fileInput.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const content = e.target.result;
            await uploadFile(file.name, content);
            showSuccess('文件上传成功');
        } catch (error) {
            showError('文件上传失败: ' + error.message);
        }
    };
    reader.readAsText(file);
}

async function uploadFile(filename, content) {
    const response = await fetch('/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filename,
            content
        })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// 搜索功能
function toggleSearch() {
    isSearchEnabled = elements.searchToggle.checked;
    elements.searchStatus.textContent = isSearchEnabled ? '搜索已启用' : '搜索已禁用';
}

// 对话管理
async function createNewConversation() {
    try {
        const response = await fetch('/conversations', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to create new conversation');
        }
        
        const newConversation = await response.json();
        
        // 清空当前对话内容
        elements.responseContainer.innerHTML = '';
        elements.messageInput.value = '';
        currentConversationId = newConversation.id;
        
        // 重新加载对话列表
        await loadConversations();
        
        return newConversation;
        
    } catch (error) {
        console.error('Error creating new conversation:', error);
        showError('创建新对话失败');
    }
}

async function loadConversations() {
    try {
        const response = await fetch('/conversations');
        if (!response.ok) {
            throw new Error('Failed to load conversations');
        }
        
        const conversations = await response.json();
        updateConversationsList(conversations);
        
    } catch (error) {
        console.error('Error loading conversations:', error);
        showError('加载对话列表失败');
    }
}

function updateConversationsList(conversations) {
    const list = document.querySelector('.conversations-list');
    if (!list) return;
    
    list.innerHTML = '';
    
    conversations.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
    
    conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = `conversation-item ${conv.id === currentConversationId ? 'active' : ''}`;
        
        // 获取对话的第一条消息作为标题
        const title = conv.messages[0]?.content || '新对话';
        const truncatedTitle = title.length > 30 ? title.substring(0, 30) + '...' : title;
        
        item.innerHTML = `
            <div class="conversation-title">${truncatedTitle}</div>
            <div class="conversation-time">${formatTime(conv.updated_at)}</div>
            <button class="delete-conversation" data-id="${conv.id}">
                <i class="fas fa-trash"></i>
            </button>
        `;
        
        // 点击加载对话
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-conversation')) {
                loadConversation(conv.id);
            }
        });
        
        // 删除对话
        const deleteBtn = item.querySelector('.delete-conversation');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm('确定要删除这个对话吗？')) {
                    await deleteConversation(conv.id);
                }
            });
        }
        
        list.appendChild(item);
    });
}

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`/conversations/${conversationId}`);
        if (!response.ok) {
            throw new Error('Failed to load conversation');
        }
        
        const conversation = await response.json();
        currentConversationId = conversationId;
        
        // 清空当前对话内容
        elements.responseContainer.innerHTML = '';
        
        // 重新渲染所有消息
        conversation.messages.forEach(msg => {
            appendMessage(msg.content, msg.role);
        });
        
        // 更新UI状态
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.toggle('active', item.dataset.id === conversationId);
        });
        
    } catch (error) {
        console.error('Error loading conversation:', error);
        showError('加载对话失败');
    }
}

async function deleteConversation(conversationId) {
    try {
        const response = await fetch(`/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete conversation');
        }
        
        // 如果删除的是当前对话，创建新对话
        if (conversationId === currentConversationId) {
            await createNewConversation();
        }
        
        // 重新加载对话列表
        await loadConversations();
        
    } catch (error) {
        console.error('Error deleting conversation:', error);
        showError('删除对话失败');
    }
}

// 格式化时间
function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // 24小时内显示具体时间
    if (diff < 24 * 60 * 60 * 1000) {
        return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // 超过24小时显示日期
    return date.toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric'
    });
}

// 工具函数
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i>${message}`;
    elements.responseContainer.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i>${message}`;
    elements.responseContainer.appendChild(successDiv);
    setTimeout(() => successDiv.remove(), 3000);
}

function toggleReasoning(reasoningDiv, button) {
    const isCollapsed = reasoningDiv.classList.contains('collapsed');
    reasoningDiv.classList.toggle('collapsed');
    button.innerHTML = isCollapsed ? '收起' : '展开';
    
    // Ensure content is visible when expanded
    if (!isCollapsed) {
        reasoningDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function updateBotMessage(content) {
    ChatState.updateContent(content);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadConversations();
});
