// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const html = document.documentElement;

    darkModeToggle.addEventListener('click', () => {
        html.classList.toggle('dark');
        localStorage.setItem('darkMode', html.classList.contains('dark'));
    });

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        html.classList.add('dark');
    }

    // WebSocket connection
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    let currentChat = null;

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    function handleWebSocketMessage(data) {
        switch(data.type) {
            case 'message':
                appendMessage(data);
                break;
            case 'catchup_request':
                handleCatchupRequest(data);
                break;
            case 'connection_update':
                updateConnectionsList();
                break;
        }
    }

    // Message handling
    function appendMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `p-2 rounded ${
            message.from_user === currentUserId 
                ? 'bg-primary text-white ml-auto' 
                : 'bg-gray-200 dark:bg-gray-700 dark:text-white'
        } max-w-[70%] break-words`;
        
        if (message.file_url) {
            if (message.file_url.match(/\.(jpg|jpeg|png|gif)$/i)) {
                messageDiv.innerHTML += `<img src="/uploads/${message.file_url}" class="max-w-full rounded">`;
            } else {
                messageDiv.innerHTML += `<a href="/uploads/${message.file_url}" class="text-blue-500 underline" target="_blank">
                    📎 ${message.file_url}</a>`;
            }
        }
        
        messageDiv.innerHTML += `<p>${message.content}</p>
            <span class="text-xs opacity-75">${new Date(message.timestamp).toLocaleTimeString()}</span>`;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Send message
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.querySelector('#chatInput input');
    const attachmentBtn = document.getElementById('attachmentBtn');
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.pdf,.png,.jpg,.jpeg,.gif';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    async function sendMessage() {
        if (!messageInput.value.trim() && !fileInput.files.length) return;

        const formData = new FormData();
        formData.append('content', messageInput.value);
        if (fileInput.files.length) {
            formData.append('file', fileInput.files[0]);
        }
        if (currentChat) {
            if (currentChat.type === 'user') {
                formData.append('to_user', currentChat.id);
            } else {
                formData.append('to_group', currentChat.id);
            }
        }

        try {
            const response = await fetch('/send_message', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                messageInput.value = '';
                fileInput.value = '';
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    attachmentBtn.addEventListener('click', () => fileInput.click());

    // Search functionality
    const searchInput = document.querySelector('input[placeholder="Search users..."]');
    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const response = await fetch(`/search_users?query=${e.target.value}`);
            const data = await response.json();
            updateSearchResults(data.users);
        }, 300);
    });

    function updateSearchResults(users) {
        const searchResults = document.createElement('div');
        searchResults.className = 'absolute bg-white dark:bg-gray-800 w-full shadow-lg rounded-lg mt-1';
        users.forEach(user => {
            const userDiv = document.createElement('div');
            userDiv.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer';
            userDiv.textContent = user.username;
            userDiv.onclick = () => sendCatchupRequest(user.id);
            searchResults.appendChild(userDiv);
        });
        
        const existingResults = document.querySelector('.search-results');
        if (existingResults) existingResults.remove();
        
        if (users.length > 0) {
            searchInput.parentElement.appendChild(searchResults);
        }
    }

    // Catch-up (Connection) Request
    async function sendCatchupRequest(userId) {
        try {
            const response = await fetch('/send_catchup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ to_user: userId })
            });
            const data = await response.json();
            if (data.success) {
                showNotification('Catch-up request sent! ⚾');
            }
        } catch (error) {
            console.error('Error sending catch-up request:', error);
        }
    }

    // Groups functionality
    const createGroupBtn = document.getElementById('createGroupBtn');
    const createGroupModal = document.getElementById('createGroupModal');

    createGroupBtn.addEventListener('click', () => {
        createGroupModal.classList.remove('hidden');
        createGroupModal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-md w-full">
                <h2 class="text-2xl font-bold mb-4 dark:text-white">Create Baseball Group</h2>
                <input type="text" id="groupName" placeholder="Group Name" 
                       class="w-full p-2 mb-4 rounded border dark:bg-gray-700 dark:text-white">
                <textarea id="groupDescription" placeholder="Group Description" 
                          class="w-full p-2 mb-4 rounded border dark:bg-gray-700 dark:text-white"></textarea>
                <div class="flex justify-end gap-2">
                    <button id="cancelGroupBtn" class="px-4 py-2 rounded bg-gray-300 dark:bg-gray-600">Cancel</button>
                    <button id="confirmGroupBtn" class="px-4 py-2 rounded bg-primary text-white">Create</button>
                </div>
            </div>
        `;

        document.getElementById('cancelGroupBtn').onclick = () => {
            createGroupModal.classList.add('hidden');
        };

        document.getElementById('confirmGroupBtn').onclick = async () => {
            const name = document.getElementById('groupName').value;
            const description = document.getElementById('groupDescription').value;
            
            if (!name.trim()) {
                showNotification('Please enter a group name!', 'error');
                return;
            }

            try {
                const response = await fetch('/create_group', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name, description })
                });
                const data = await response.json();
                if (data.success) {
                    createGroupModal.classList.add('hidden');
                    showNotification('Group created successfully! ⚾');
                    updateGroupsList();
                }
            } catch (error) {
                console.error('Error creating group:', error);
            }
        };
    });

    // Update lists
    async function updateConnectionsList() {
        try {
            const response = await fetch('/get_connections');
            const data = await response.json();
            const connectionsList = document.getElementById('connectionsList');
            connectionsList.innerHTML = '';
            
            data.connections.forEach(connection => {
                const connDiv = document.createElement('div');
                connDiv.className = 'p-2 bg-white dark:bg-gray-700 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600';
                connDiv.innerHTML = `
                    <div class="flex items-center gap-2">
                        <img src="${connection.profile_pic}" alt="" class="w-8 h-8 rounded-full">
                        <span class="dark:text-white">${connection.username}</span>
                    </div>
                `;
                connDiv.onclick = () => openChat('user', connection.id);
                connectionsList.appendChild(connDiv);
            });
        } catch (error) {
            console.error('Error updating connections:', error);
        }
    }

    async function updateGroupsList() {
        try {
            const response = await fetch('/get_groups');
            const data = await response.json();
            const groupsList = document.getElementById('groupsList');
            groupsList.innerHTML = '';
            
            data.groups.forEach(group => {
                const groupDiv = document.createElement('div');
                groupDiv.className = 'p-2 bg-white dark:bg-gray-700 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600';
                groupDiv.innerHTML = `
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⚾</span>
                        <span class="dark:text-white">${group.name}</span>
                    </div>
                `;
                groupDiv.onclick = () => openChat('group', group.id);
                groupsList.appendChild(groupDiv);
            });
        } catch (error) {
            console.error('Error updating groups:', error);
        }
    }

    // Chat handling
    function openChat(type, id) {
        currentChat = { type, id };
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
        loadChatHistory(type, id);
        
        // Update chat header
        const chatHeader = document.getElementById('chatHeader');
        chatHeader.innerHTML = `
            <div class="flex items-center gap-2">
                <h2 class="text-2xl font-bold dark:text-white">
                    ${type === 'user' ? 'Chat with ' + getUserName(id) : getGroupName(id)}
                </h2>
            </div>
        `;
    }

    async function loadChatHistory(type, id) {
        try {
            const response = await fetch(`/get_messages?type=${type}&id=${id}`);
            const data = await response.json();
            data.messages.forEach(message => appendMessage(message));
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    // Utility functions
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded shadow-lg ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    function getUserName(id) {
        // This should be replaced with actual user data from your application state
        return `User ${id}`;
    }

    function getGroupName(id) {
        // This should be replaced with actual group data from your application state
        return `Group ${id}`;
    }

    // Initial loads
    updateConnectionsList();
    updateGroupsList();
});