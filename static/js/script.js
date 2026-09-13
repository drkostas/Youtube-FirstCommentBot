// script.js
document.addEventListener('DOMContentLoaded', () => {
    const channelsContainer = document.getElementById('channels-section');
    const commentsContainer = document.getElementById('comments-section');
    const addChannelModal = document.getElementById('add-channel-modal');
    const addChannelBtn = document.getElementById('add-channel-btn');
    const closeBtn = document.querySelector('.close');
    const addChannelForm = document.getElementById('add-channel-form');
    const refreshBtn = document.getElementById('refresh-btn');

    function formatDateTime(dateTimeStr) {
        const date = new Date(dateTimeStr);
        const year = date.getFullYear().toString().slice(-2);
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    }

    function formatNumber(num) {
        return Number(num).toFixed(1);
    }

    function makeApiCall(url, method, body = null) {
        return fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: body ? JSON.stringify(body) : null
        }).then(response => response.json());
    }

    // Fetch and display channels
    function fetchChannels() {
        makeApiCall('/get_channels', 'GET')
            .then(channels => {
                channelsContainer.innerHTML = ''; // Clear existing content
                channels.forEach(channel => {
                    const channelCard = createChannelCard(channel);
                    channelsContainer.appendChild(channelCard);
                });
            })
            .catch(error => console.error('Failed to fetch channels:', error));
    }

    // Create a channel card element
    function createChannelCard(channel) {
        const card = document.createElement('div');
        card.className = 'channel-card';

        card.innerHTML = `
        <div class="channel-header">
            <img src="${channel.channel_photo}" alt="${channel.username}" class="channel-image">
            <h3 class="channel-name">${channel.username}</h3>
            <span class="stats">
                ${formatNumber(channel.avg_likes)} likes
                <br>${formatNumber(channel.avg_replies)} replies
                <br>${channel.banned_count}/${channel.count} bans
                <br>${formatDateTime(new Date(channel.last_commented).toLocaleString())} commented
            </span>
        </div>
        <div class="channel-actions">
            <input type="number" value="${channel.priority}" class="priority-input" data-channel-id="${channel.channel_id}">
            <input type="number" value="${channel.delay_comment}" class="delay-input" data-channel-id="${channel.channel_id}">
            <button data-channel-id="${channel.channel_id}" class="update-btn" onclick="updateChannel('${channel.channel_id}')">Update</button>
            <label class="switch">
                <input type="checkbox" ${channel.active ? 'checked' : ''} onchange="toggleActive('${channel.channel_id}', this.checked)">
                <span class="slider round"></span>
            </label>
        </div>
        `;
        return card;
    }

    // Fetch and display comments
    function fetchComments() {
        fetch('/get_comments')
            .then(response => response.json())
            .then(comments => {
                commentsContainer.innerHTML = ''; // Clear existing content
                comments.forEach(comment => {
                    const commentCard = createCommentCard(comment);
                    commentsContainer.appendChild(commentCard);
                });
            })
            .catch(error => console.error('Failed to fetch comments:', error));
    }

    // Create a comment card element
    function createCommentCard(comment) {
        const card = document.createElement('div');
        card.className = 'comment-card';

        let link = comment.comment_link !== "-1" ? comment.comment_link : comment.video_link;

        card.innerHTML = `
        <div class="comment-header">
            <img src="${comment.channel_photo}" alt="${comment.username}" class="comment-image">
            <div class="comment-meta">
                <h4 class="channel-name">${comment.username}</h4>
                <time class="comment-time stats">${formatDateTime(new Date(comment.comment_time).toLocaleString())}</time>
            </div>
        </div>
        <div class="comment-body">
            <p class="comment-text">${comment.comment}</p>
            <div class="comment-stats">
                <span class="stats">Likes: ${comment.like_count}</span>
                <span class="stats">Replies: ${comment.reply_count}</span>
            </div>
            <button onclick="parent.open('${link}')" class="open-comment">Open Comment</button>
        </div>
        `;
        return card;
    }

    function refreshPhotos() {
        // Send the request to the server endpoint for updating priority
        makeApiCall('/refresh_photos', 'POST', {})
            .then(response => {
                if (response.message) {
                    console.log(response.message);
                    // Optionally refresh the channels list or update the UI
                    fetchChannels();
                } else {
                    console.error('Failed to refresh photos:', response.error);
                }
            })
            .catch(error => {
                console.error('Failed to refresh photos:', error);
            });
    }


    // Define the updateChannel function
    window.updateChannel = (channelId) => {
        const priorityInput = document.querySelector(`.priority-input[data-channel-id="${channelId}"]`);
        const delayInput = document.querySelector(`.delay-input[data-channel-id="${channelId}"]`);
        // const activeInput = document.querySelector(`.active-input[data-channel-id="${channelId}"]:checked`);
        // active: activeInput ? true : false
        const data = {
            channel_id: channelId,
            priority: priorityInput.value,
            delay_comment: delayInput.value,
        };

        makeApiCall('/update_channel', 'POST', data)
            .then(response => {
                if (response.message) {
                    console.log(response.message);
                    fetchChannels(); // Refresh the channels list
                } else {
                    console.error('Failed to update priority:', response.error);
                }
            })
            .catch(error => {
                console.error('Failed to update priority:', error);
            });
    };

    refreshBtn.addEventListener('click', () => {
        refreshPhotos();
    });


    // Define the toggleActive function
    window.toggleActive = (channelId, isActive) => {
        const data = { active: isActive };
        fetch(`/toggle_active/${channelId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                fetchChannels(); // Refresh the channels list
            })
            .catch(error => console.error('Failed to toggle channel active status:', error));
    };

    // Event listeners for the add channel modal
    addChannelBtn.addEventListener('click', () => {
        addChannelModal.style.display = 'block';
    });

    closeBtn.addEventListener('click', () => {
        addChannelModal.style.display = 'none';
    });

    addChannelForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const channelIdInput = document.getElementById('channel-id');
        const channelId = channelIdInput.value;
        fetch('/add_channel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_id: channelId })
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                fetchChannels(); // Refresh the channels list
                channelIdInput.value = ''; // Clear the input
                addChannelModal.style.display = 'none'; // Close the modal
            })
            .catch(error => console.error('Failed to add channel:', error));
    });

    window.onclick = (event) => {
        if (event.target === addChannelModal) {
            addChannelModal.style.display = 'none';
        }
    };


    // Fetch initial data
    fetchChannels();
    fetchComments();
});

