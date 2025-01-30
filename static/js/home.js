document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    let searchTimeout;

    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        if (searchInput.value.length < 2) {
            searchResults.innerHTML = '';
            searchResults.classList.add('hidden');
            return;
        }

        // Add debounce to prevent too many requests
        searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/search_users?query=${encodeURIComponent(searchInput.value)}`);
                const data = await response.json();

                if (!data.success && data.error) {
                    throw new Error(data.error);
                }

                let resultsHTML = '';

                // Add users results
                if (data.users && data.users.length > 0) {
                    resultsHTML += '<div class="p-2 bg-gray-100 font-semibold">Users</div>';
                    data.users.forEach(user => {
                        resultsHTML += `
                    <div class="flex items-center justify-between p-4 hover:bg-gray-50">
                        <span>${user}</span>
                        <button 
                            onclick="sendRequest('${user}')"
                            class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                        >
                            Add Friend
                        </button>
                    </div>
                `;
                    });
                }

                // Add groups results
                if (data.groups && data.groups.length > 0) {
                    resultsHTML += '<div class="p-2 bg-gray-100 font-semibold">Groups</div>';
                    data.groups.forEach(group => {
                        resultsHTML += `
                    <div class="flex items-center justify-between p-4 hover:bg-gray-50">
                        <div>
                            <div class="font-medium">${group.group_name}</div>
                            <div class="text-sm text-gray-600">${group.description}</div>
                        </div>
                        <button 
                            onclick="joinGroup('${group.group_id}')"
                            class="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors"
                        >
                            Join Group
                        </button>
                    </div>
                `;
                    });
                }

                if (!resultsHTML) {
                    resultsHTML = '<div class="p-4 text-gray-500">No results found</div>';
                }

                searchResults.innerHTML = resultsHTML;
                searchResults.classList.remove('hidden');
            } catch (error) {
                console.error('Search error:', error);
                searchResults.innerHTML = '<div class="p-4 text-red-500">Error performing search</div>';
            }
        }, 300);
    });

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });

    // Friend request functions
    window.sendRequest = async function (toUser) {
        try {
            const formData = new FormData();
            formData.append('to_user', toUser);

            const response = await fetch('/send_request', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Show success message
                const toast = document.createElement('div');
                toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg';
                toast.textContent = `Friend request sent to ${toUser}`;
                document.body.appendChild(toast);

                // Remove toast after 3 seconds
                setTimeout(() => toast.remove(), 3000);
            } else {
                throw new Error('Failed to send request');
            }
        } catch (error) {
            console.error('Error sending friend request:', error);
            alert('Failed to send friend request. Please try again.');
        }
    };

    window.acceptRequest = async function (fromUser) {
        try {
            const formData = new FormData();
            formData.append('from_user', fromUser);

            const response = await fetch('/accept_request', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                throw new Error('Failed to accept request');
            }
        } catch (error) {
            console.error('Error accepting friend request:', error);
            alert('Failed to accept friend request. Please try again.');
        }
    };

    window.startChat = function (friendName) {
        // Implement chat functionality or redirect to chat page
        alert('Chat functionality coming soon!');
    };

    window.joinGroup = function (groupId) {
        // Implement group join functionality
        fetch(`/join_group/${groupId}`, {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    throw new Error(data.error || 'Failed to join group');
                }
            })
            .catch(error => {
                console.error('Error joining group:', error);
                alert('Failed to join group. Please try again.');
            });
    };
});

async function createGroup() {
    const groupName = document.getElementById('groupName').value;
    const groupDescription = document.getElementById('groupDescription').value;

    if (!groupName) {
        alert("Group name is required!");
        return;
    }

    const response = await axios.post('/create_group', {
        group_name: groupName,
        description: groupDescription
    });

    if (response.data.success) {
        alert('Group created successfully');
        window.location.href = `/group_chat/${response.data.group_id}`;
    } else {
        alert('Failed to create group: ' + response.data.error);
    }
}

async function joinGroup(groupId) {
    try {
        const response = await axios.post(`/join_group/${groupId}`);
        if (response.data.success) {
            alert('Joined group successfully!');
            location.reload();
        } else {
            alert('Failed to join group: ' + response.data.error);
        }
    } catch (error) {
        console.error('Error joining group:', error);
        alert('Failed to join group');
    }
}

async function leaveGroup(groupId) {
    if (!confirm('Are you sure you want to leave this group?')) {
        return;
    }

    try {
        const response = await axios.post(`/leave_group/${groupId}`);
        if (response.data.success) {
            alert('Left group successfully!');
            location.reload();
        } else {
            alert('Failed to leave group: ' + response.data.error);
        }
    } catch (error) {
        console.error('Error leaving group:', error);
        alert('Failed to leave group');
    }
}
// Sidebar Toggle
document.getElementById('sidebar-toggle').addEventListener('click', function () {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('hidden');
});

// News Toggle
document.getElementById('news-toggle').addEventListener('click', function () {
    const newsSection = document.getElementById('news-section');
    newsSection.classList.toggle('hidden');
});

document.getElementById('close-news').addEventListener('click', function () {
    document.getElementById('news-section').classList.add('hidden');
});

// Chatbot Toggle
document.getElementById('chatbot-trigger').addEventListener('click', function () {
    const chatbotContainer = document.getElementById('chatbot-container');
    chatbotContainer.classList.toggle('hidden');
});

document.getElementById('close-chatbot').addEventListener('click', function () {
    document.getElementById('chatbot-container').classList.add('hidden');
});

// Dark Mode Toggle
document.getElementById('darkModeToggle').addEventListener('click', function () {
    document.documentElement.classList.toggle('dark');

    // Update icon
    const icon = this.querySelector('i');
    if (document.documentElement.classList.contains('dark')) {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }

    // Save preference
    const isDark = document.documentElement.classList.contains('dark');
    localStorage.setItem('darkMode', isDark);
});

// Initialize dark mode from saved preference
document.addEventListener('DOMContentLoaded', function () {
    const isDark = localStorage.getItem('darkMode') === 'true';
    if (isDark) {
        document.documentElement.classList.add('dark');
        const icon = document.querySelector('#darkModeToggle i');
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    }
});

// Team dropdown hover
const teamDropdown = document.querySelector('.group');
teamDropdown.addEventListener('mouseenter', function () {
    this.querySelector('div').classList.remove('hidden');
});
teamDropdown.addEventListener('mouseleave', function () {
    this.querySelector('div').classList.add('hidden');
});

// Chatbot send message functionality
document.getElementById('send-message').addEventListener('click', sendChatMessage);
document.getElementById('chatbot-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
});

function sendChatMessage() {
    const input = document.getElementById('chatbot-input');
    const message = input.value.trim();
    if (message) {
        const messagesContainer = document.getElementById('chatbot-messages');

        // Add user message
        const userMessage = document.createElement('div');
        userMessage.className = 'mb-4 text-right';
        userMessage.innerHTML = `
    <span class="inline-block bg-[#213a8f] text-white rounded-lg py-2 px-4 max-w-[80%]">
        ${message}
    </span>
`;
        messagesContainer.appendChild(userMessage);

        // Clear input
        input.value = '';

        // Auto scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Here you would typically send the message to your backend
        // and handle the response
    }
}

