document.addEventListener('DOMContentLoaded', () => {
    // 初始化搜索和处理按钮
    const searchButton = document.getElementById('search-button');
    const processButton = document.getElementById('process-button');
    const searchInput = document.getElementById('search-input');
    const monthInput = document.getElementById('month-input');

    searchButton.addEventListener('click', handleSearch);
    processButton.addEventListener('click', handleProcessData);
    
    searchInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            handleSearch();
        }
    });
    
    // 设置月份输入框的默认值为当前月份
    if (monthInput) {
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = (currentDate.getMonth() + 1).toString().padStart(2, '0');
        monthInput.value = `${currentYear}-${currentMonth}`;
        console.log(`默认月份已设置为: ${monthInput.value}`);
    } else {
        console.error('找不到 #month-input 元素');
    }

    // 加载保存的笔记（如果需要）
    // loadSavedNotes();
    
    // 初始化任务列如果需要）
    // initTaskList();

    // 初始化 Todo List
    initTodoList();

    // 添加导航切换功能
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-target');
            console.log('切换到页面:', targetId);
            switchPage(targetId);
        });
    });

    // 初始化显示主页
    switchPage('home');

    const specialExpenseNote = document.getElementById('special-expense-note');
    const assistantExpenseNote = document.getElementById('assistant-expense-note');

    // 从本地存储加载内容
    specialExpenseNote.textContent = localStorage.getItem('specialExpenseNote') || '在这里记录特约费用...';
    assistantExpenseNote.textContent = localStorage.getItem('assistantExpenseNote') || '在这里记录学生助理费用...';

    // 保存内容到本地存储
    specialExpenseNote.addEventListener('input', function() {
        localStorage.setItem('specialExpenseNote', this.textContent);
    });

    assistantExpenseNote.addEventListener('input', function() {
        localStorage.setItem('assistantExpenseNote', this.textContent);
    });

    const pageFeeContent = document.getElementById('page-fee-content');
    if (pageFeeContent) {
        loadPageFeeData();
    }

    const scrapingForm = document.getElementById('scraping-form');
    if (scrapingForm) {
        const yearInput = document.getElementById('year-input');
        const issueInput = document.getElementById('issue-input');
        
        // 设置默认年份和期数
        const currentDate = new Date();
        yearInput.value = currentDate.getFullYear();
        issueInput.value = currentDate.getMonth() + 1; // 假设期数与月份对应

        scrapingForm.addEventListener('submit', handleScraping);
    }

    // 初始化记事本
    initNotes();

    initAIChat();
});

function switchPage(pageId) {
    console.log('切换到页面:', pageId); // 添加日志

    // 隐藏所有页面
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
        page.style.display = 'none'; // 确保页面被隐藏
    });

    // 显示目标页面
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
        targetPage.style.display = 'block'; // 确保页面被显示
        console.log('目标页面已激活:', pageId);
    } else {
        console.error(`找不到页面 ID: ${pageId}`);
    }

    // 更新导航栏活动状态
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-target') === pageId) {
            link.classList.add('active');
            console.log('导航链接已激活:', pageId);
        }
    });
}

async function handleProcessData() {
    const monthInput = document.getElementById('month-input');
    const selectedMonth = monthInput.value;

    if (!selectedMonth) {
        alert('请选择一个月份');
        return;
    }

    const resultDiv = document.getElementById('review-result');
    resultDiv.innerHTML = '<p>正在处理数据...</p>';

    try {
        const response = await fetch('/process_review', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ target_month: selectedMonth }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.message) {
            resultDiv.innerHTML = `<p>${data.message}</p><p>文件保存在：${data.file}</p>`;
        } else {
            resultDiv.innerHTML = `<p>错误: ${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p>错误: ${error.message}</p>`;
    }
}

async function handleSearch() {
    const searchType = document.getElementById('search-type').value;
    const searchValue = document.getElementById('search-input').value.trim();
    const resultDiv = document.getElementById('search-result');

    if (!searchValue) {
        resultDiv.innerHTML = '<p>请输入搜索内容😡😡😡</p>';
        resultDiv.style.display = 'block';
        return;
    }

    try {
        let response;
        switch (searchType) {
            case 'employee':
                response = await fetch(`/query_employee?name=${encodeURIComponent(searchValue)}`);
                break;
            case 'id':
                response = await fetch(`/query_employee?employee_id=${encodeURIComponent(searchValue)}`);
                break;
            case 'manuscript':
                response = await fetch(`/query_manuscript?query=${encodeURIComponent(searchValue)}`);
                break;
            default:
                throw new Error('未知的搜索类型');
        }
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '未知错误');
        }
        const data = await response.json();
        displayFormattedResult(data);
    } catch (error) {
        resultDiv.innerHTML = `<p>错误: ${error.message}</p>`;
        resultDiv.style.display = 'block';
    }
}

function displayFormattedResult(data) {
    const resultDiv = document.getElementById('search-result');
    resultDiv.innerHTML = '';

    if (data.type === 'employee') {
        // 员工信息显示 - 支持多条结果
        resultDiv.innerHTML = `
            <h3>职工信息</h3>
            <div class="employee-results">
                ${data.data.map(emp => `
                    <div class="employee-card">
                        <p><strong>姓名:</strong> ${emp.姓名}</p>
                        <p><strong>工号:</strong> ${emp.工号}</p>
                        <p><strong>部门:</strong> ${emp.部门}</p>
                    </div>
                `).join('')}
            </div>
            <button onclick="closeSearchResult()">关闭</button>
        `;
    } else if (data.type === 'manuscript') {
        // 审稿信息显示
        resultDiv.innerHTML = `
            <h3>审稿信息</h3>
            <div class="manuscript-container">
                <div class="manuscript-column">
                    <h4>评审记录</h4>
                    ${formatManuscriptData(data.data.review)}
                </div>
                <div class="manuscript-column">
                    <h4>复审记录</h4>
                    ${formatManuscriptData(data.data.re_review)}
                </div>
            </div>
            <button onclick="closeSearchResult()">关闭</button>
        `;
    } else {
        resultDiv.innerHTML = '<p>未知的数据类型</p>';
    }

    resultDiv.style.display = 'block';
}

function closeSearchResult() {
    const resultDiv = document.getElementById('search-result');
    resultDiv.style.display = 'none';
}

function formatManuscriptData(records) {
    if (!records || records.length === 0) {
        return '<p>无记录</p>';
    }
    return records.map(record => `
        <div class="manuscript-record">
            <p><strong>稿件编号:</strong> ${record.稿件编号}</p>
            <p><strong>审稿人姓名:</strong> ${record.审稿人姓名}</p>
            <p><strong>审回时间:</strong> ${new Date(record.审回时间).toLocaleDateString('zh-CN')}</p>
        </div>
    `).join('');
}

function initTodoList() {
    const addTaskButton = document.getElementById('add-task');
    const taskInput = document.getElementById('task-input');
    const taskList = document.getElementById('task-list');

    addTaskButton.addEventListener('click', addTask);
    taskInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addTask();
        }
    });

    loadTasks();
}

function addTask() {
    const taskInput = document.getElementById('task-input');
    const taskText = taskInput.value.trim();
    if (taskText) {
        const task = {
            id: Date.now(),
            text: taskText,
            starred: false,
            createdAt: new Date().toISOString(),
            completed: false
        };
        const tasks = getTasks();
        tasks.push(task);
        saveTasks(tasks);
        renderTasks();
        taskInput.value = '';
    }
}

function getTasks() {
    return JSON.parse(localStorage.getItem('tasks') || '[]');
}

function saveTasks(tasks) {
    localStorage.setItem('tasks', JSON.stringify(tasks));
}

function renderTasks() {
    const taskList = document.getElementById('task-list');
    const tasks = getTasks().sort((a, b) => {
        if (a.completed !== b.completed) {
            return a.completed ? 1 : -1;
        }
        if (a.starred !== b.starred) {
            return b.starred - a.starred;
        }
        return new Date(b.createdAt) - new Date(a.createdAt);
    });

    taskList.innerHTML = '';
    tasks.forEach(task => {
        const li = document.createElement('li');
        li.className = `task-item ${task.completed ? 'completed' : ''}`;
        li.innerHTML = `
            <input type="checkbox" class="task-checkbox" ${task.completed ? 'checked' : ''}>
            <span class="task-text">${task.text}</span>
            <div class="task-actions">
                <button class="star-task" onclick="toggleStar(${task.id})">${task.starred ? '★' : '☆'}</button>
                <button class="delete-task" onclick="deleteTask(${task.id})">🗑️</button>
            </div>
        `;
        taskList.appendChild(li);

        const checkbox = li.querySelector('.task-checkbox');
        checkbox.addEventListener('change', () => toggleCompleted(task.id));

        const taskText = li.querySelector('.task-text');
        taskText.addEventListener('click', () => makeEditable(taskText, task.id));
        taskText.addEventListener('blur', () => saveEdit(taskText, task.id));
        taskText.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                taskText.blur();
            }
        });
    });
}

function toggleCompleted(taskId) {
    const tasks = getTasks();
    const task = tasks.find(t => t.id === taskId);
    if (task) {
        task.completed = !task.completed;
        saveTasks(tasks);
        renderTasks();
    }
}

function makeEditable(element, taskId) {
    element.contentEditable = true;
    element.classList.add('editable');
    element.focus();
}

function saveEdit(element, taskId) {
    element.contentEditable = false;
    element.classList.remove('editable');
    const newText = element.textContent.trim();
    if (newText) {
        const tasks = getTasks();
        const task = tasks.find(t => t.id === taskId);
        if (task) {
            task.text = newText;
            saveTasks(tasks);
        }
    }
    renderTasks();
}

function toggleStar(taskId) {
    const tasks = getTasks();
    const task = tasks.find(t => t.id === taskId);
    if (task) {
        task.starred = !task.starred;
        saveTasks(tasks);
        renderTasks();
    }
}

function deleteTask(taskId) {
    const tasks = getTasks().filter(t => t.id !== taskId);
    saveTasks(tasks);
    renderTasks();
}

function loadTasks() {
    renderTasks();
}

async function loadPageFeeData(filter = 'all') {
    try {
        console.log('开始加载版面费数据');
        const response = await fetch(`/get_page_fee_data?filter=${filter}`);
        console.log('收到服务器响应:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('解析到的数据:', data);
        if (Array.isArray(data) && data.length === 0) {
            console.log('数据为空数组');
            document.getElementById('page-fee-content').innerHTML = '<p>没有找到版面费数据。</p>';
        } else {
            displayPageFeeData(data);
        }
    } catch (error) {
        console.error('加载版面费数据失败:', error);
        document.getElementById('page-fee-content').innerHTML = `<p>加载数据时出错: ${error.message}</p>`;
    }
}

function displayPageFeeData(data) {
    const pageFeeContent = document.getElementById('page-fee-content');
    pageFeeContent.innerHTML = `
        <h3>现有记录</h3>
        <div class="table-controls">
            <label>筛选：</label>
            <select id="filter-select">
                <option value="all">全部</option>
                <option value="unprocessed">未处理</option>
            </select>
        </div>
        <div class="table-container">
            <table id="page-fee-table">
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>稿件编号</th>
                        <th>备注</th>
                        <th>核销号</th>
                        <th>财务备注</th>
                        <th>税号</th>
                        <th>发票抬头</th>
                        <th>邮箱</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(item => `
                        <tr>
                            <td>
                                <input type="checkbox" class="status-checkbox" data-type="录用" data-manuscript="${item.稿件编号}" ${item.录用 ? 'checked' : ''}>
                                <input type="checkbox" class="status-checkbox" data-type="发票" data-manuscript="${item.稿件编号}" ${item.发票 ? 'checked' : ''}>
                            </td>
                            <td class="manuscript-number" title="${item.稿件编号}">${item.稿件编号}</td>
                            <td>${item.备注 || ''}</td>
                            <td>${item.核销号 || ''}</td>
                            <td>${item.财务备注 || ''}</td>
                            <td>${item.税号 || ''}</td>
                            <td>${item.发票抬头 || ''}</td>
                            <td>${item.邮箱 || ''}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    // 添加复选框变更事件监听器
    document.querySelectorAll('.status-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', handleStatusChange);
    });

    // 添加筛选变更事件监听器
    document.getElementById('filter-select').addEventListener('change', handleFilterChange);
}

async function handleStatusChange(event) {
    const checkbox = event.target;
    const manuscriptNumber = checkbox.dataset.manuscript;
    const statusType = checkbox.dataset.type;
    const isChecked = checkbox.checked;

    try {
        const response = await fetch('/update_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                稿件编号: manuscriptNumber,
                statusType: statusType,
                isChecked: isChecked
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log(result.message);
    } catch (error) {
        console.error('更新状态失败:', error);
        alert('更新状态失败: ' + error.message);
        // 恢复复选框状态
        checkbox.checked = !isChecked;
    }
}

async function handleFilterChange(event) {
    const filterValue = event.target.value;
    await loadPageFeeData(filterValue);
}

// 确保在页面加载完成后调用 loadPageFeeData
document.addEventListener('DOMContentLoaded', () => {
    const pageFeeContent = document.getElementById('page-fee-content');
    if (pageFeeContent) {
        loadPageFeeData();
    }
});

async function handleScraping(event) {
    event.preventDefault();
    const yearInput = document.getElementById('year-input');
    const issueInput = document.getElementById('issue-input');
    const resultDiv = document.getElementById('scraping-result');

    const year = yearInput.value;
    const issue = issueInput.value;

    resultDiv.innerHTML = '<p class="info">正在爬取数据,请稍候...</p>';

    try {
        const response = await fetch('/start_scraping', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ year, issue }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayScrapingResult(data, resultDiv);
    } catch (error) {
        console.error('爬虫任务失败:', error);
        resultDiv.innerHTML = `<p class="error">爬虫任务失败: ${error.message}</p>`;
    }
}

function displayScrapingResult(data, resultDiv) {
    const { year, issue, articles_count, processed_articles } = data;
    
    let resultHTML = `
        <h4>爬虫任务完成</h4>
        <p><strong>年份:</strong> ${year}</p>
        <p><strong>期数:</strong> ${issue}</p>
        <p><strong>文章数量:</strong> ${articles_count}</p>
        <h5>处理的文章:</h5>
        <ul class="article-list">
    `;

    processed_articles.forEach(article => {
        resultHTML += `
            <li>
                <span class="article-title">${article.title}</span>
                <span class="article-path">${article.image_path}</span>
            </li>
        `;
    });

    resultHTML += '</ul>';
    resultDiv.innerHTML = resultHTML;
}

function initNotes() {
    const notes = [
        { id: 'special-expense-note', key: 'specialExpenseNote' },
        { id: 'assistant-expense-note', key: 'assistantExpenseNote' },
        { id: 'manuscript-fee-pending', key: 'manuscriptFeePending' },
        { id: 'manuscript-fee-reimbursement', key: 'manuscriptFeeReimbursement' },
        { id: 'review-fee-processed', key: 'reviewFeeProcessed' },
        { id: 'review-fee-reimbursement', key: 'reviewFeeReimbursement' }
    ];

    // 从服务器加载笔记
    fetch('/load_notes')
        .then(response => response.json())
        .then(data => {
            notes.forEach(note => {
                const element = document.getElementById(note.id);
                if (element) {
                    element.textContent = data[note.id] || element.textContent;
                    element.addEventListener('input', debounce(function() {
                        saveNotes();
                    }, 500));
                }
            });
        })
        .catch(error => console.error('加载笔记失败:', error));
}

function saveNotes() {
    const notesData = {};
    const notes = document.querySelectorAll('.expense-note');
    notes.forEach(note => {
        notesData[note.id] = note.textContent;
    });

    fetch('/save_notes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(notesData),
    })
    .then(response => response.json())
    .then(data => console.log(data.message))
    .catch(error => console.error('保存笔记失败:', error));
}

// 添加防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 确保在页面加载完成后初始化笔记
document.addEventListener('DOMContentLoaded', initNotes);

function openFolder() {
    const button = document.getElementById('open-folder-btn');
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="emoji">⏳</span> 正在打开...';
    button.disabled = true;

    fetch('/open_folder')
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                button.innerHTML = '<span class="emoji">✅</span> ' + data.message;
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }, 2000);
            } else if (data.error) {
                alert('错误: ' + data.error);
                button.innerHTML = originalText;
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('发生错误,请查看控制台');
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

function initAIChat() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-message');

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            addMessage('user', message);
            userInput.value = '';

            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.response) {
                    const formattedResponse = formatResponse(data.response);
                    addMessage('ai', formattedResponse);
                } else if (data.error) {
                    addMessage('error', '错误: ' + data.error);
                }
            })
            .catch(error => {
                addMessage('error', '发生错误: ' + error.message);
            });
        }
    }

    function formatResponse(response) {
        return marked.parse(response);
    }

    function addMessage(sender, content) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender}`;
        messageElement.innerHTML = content;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 在文档加载完成后初始化AI聊天功能
document.addEventListener('DOMContentLoaded', initAIChat);

