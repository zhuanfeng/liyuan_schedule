document.addEventListener('DOMContentLoaded', function() {
    // 获取所有课程表输入框
    const scheduleInputs = document.querySelectorAll('.schedule-input');
    
    // 为每个输入框添加事件监听器
    scheduleInputs.forEach(input => {
        // 失去焦点时保存数据
        input.addEventListener('blur', function() {
            const date = this.dataset.date;
            const hour = this.dataset.hour;
            const studentName = this.value.trim();
            
            // 根据是否有学生名称决定是添加还是删除
            if (studentName) {
                // 添加或更新学生名称
                updateSchedule(date, hour, studentName);
                this.classList.remove('available');
                this.classList.add('booked');
            } else {
                // 删除学生名称
                deleteSchedule(date, hour);
                this.classList.remove('booked');
                this.classList.add('available');
            }
        });
        
        // 按下回车键时也保存数据
        input.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                this.blur();
            }
        });
    });
    
    // 发送添加或更新请求
    function updateSchedule(date, hour, studentName) {
        fetch('/schedule', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                hour: parseInt(hour),
                student_name: studentName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('更新失败:', data.message);
            }
        })
        .catch(error => {
            console.error('请求错误:', error);
        });
    }
    
    // 发送删除请求
    function deleteSchedule(date, hour) {
        fetch('/schedule', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                hour: parseInt(hour)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('删除失败:', data.message);
            }
        })
        .catch(error => {
            console.error('请求错误:', error);
        });
    }
});