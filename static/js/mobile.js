// 移动端优化脚本
(function() {
    'use strict';
    
    // 检测是否为移动设备
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    if (!isMobile) return;
    
    // 禁用双击缩放
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(event) {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
    
    // 添加触摸反馈
    document.addEventListener('DOMContentLoaded', function() {
        // 为所有可点击元素添加触摸反馈
        const clickables = document.querySelectorAll('a, button, .video-card, .floating-comment-input');
        
        clickables.forEach(el => {
            el.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            });
            
            el.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 100);
            });
        });
        
        // 优化滚动性能
        const scrollElements = document.querySelectorAll('.comments-list, .video-grid');
        scrollElements.forEach(el => {
            el.style.webkitOverflowScrolling = 'touch';
        });
        
        // 视频列表滑动加载更多
        if (window.location.pathname === '/') {
            let isLoading = false;
            const threshold = 100;
            
            window.addEventListener('scroll', function() {
                if (isLoading) return;
                
                const scrollHeight = document.documentElement.scrollHeight;
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const clientHeight = document.documentElement.clientHeight;
                
                if (scrollHeight - scrollTop - clientHeight < threshold) {
                    // 检查是否有下一页
                    const nextLink = document.querySelector('.pagination .page-link[href*="page="]:last-child');
                    if (nextLink && nextLink.textContent === '下一页') {
                        isLoading = true;
                        // 这里可以实现AJAX加载更多
                        console.log('Load more videos...');
                    }
                }
            });
        }
        
        // 改善表单输入体验
        const inputs = document.querySelectorAll('input[type="text"], input[type="tel"], textarea');
        inputs.forEach(input => {
            // 自动聚焦到下一个输入框
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && this.type !== 'textarea') {
                    e.preventDefault();
                    const form = this.closest('form');
                    const inputs = Array.from(form.querySelectorAll('input, textarea'));
                    const index = inputs.indexOf(this);
                    if (index < inputs.length - 1) {
                        inputs[index + 1].focus();
                    }
                }
            });
        });
        
        // PWA支持
        if ('serviceWorker' in navigator) {
            // 可以在这里注册Service Worker
            console.log('Service Worker support detected');
        }
        
        // 添加下拉刷新提示（仅在首页）
        if (window.location.pathname === '/') {
            let startY = 0;
            let isPulling = false;
            
            document.addEventListener('touchstart', function(e) {
                if (window.scrollY === 0) {
                    startY = e.touches[0].pageY;
                    isPulling = true;
                }
            });
            
            document.addEventListener('touchmove', function(e) {
                if (!isPulling) return;
                
                const currentY = e.touches[0].pageY;
                const pullDistance = currentY - startY;
                
                if (pullDistance > 80) {
                    // 显示刷新提示
                    if (!document.querySelector('.pull-to-refresh')) {
                        const refreshHint = document.createElement('div');
                        refreshHint.className = 'pull-to-refresh';
                        refreshHint.textContent = '松开刷新';
                        document.body.appendChild(refreshHint);
                    }
                }
            });
            
            document.addEventListener('touchend', function() {
                if (document.querySelector('.pull-to-refresh')) {
                    location.reload();
                }
                isPulling = false;
            });
        }
    });
    
    // 视频播放优化
    if (document.getElementById('videoPlayer')) {
        const video = document.getElementById('videoPlayer');
        
        // 添加手势控制
        let touchStartX = 0;
        let touchStartTime = 0;
        
        video.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
            touchStartTime = video.currentTime;
        });
        
        video.addEventListener('touchmove', function(e) {
            const touchX = e.touches[0].clientX;
            const deltaX = touchX - touchStartX;
            const seekTime = (deltaX / video.clientWidth) * 30; // 30秒最大跳转
            
            if (Math.abs(seekTime) > 1) {
                video.currentTime = Math.max(0, Math.min(video.duration, touchStartTime + seekTime));
            }
        });
    }
})();

// 添加触摸激活样式
const style = document.createElement('style');
style.textContent = `
    .touch-active {
        opacity: 0.7 !important;
        transform: scale(0.98) !important;
    }
    
    .pull-to-refresh {
        position: fixed;
        top: 60px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.875rem;
        z-index: 1000;
        animation: slideDown 0.3s ease-out;
    }
    
    @keyframes slideDown {
        from {
            transform: translateX(-50%) translateY(-100%);
        }
        to {
            transform: translateX(-50%) translateY(0);
        }
    }
`;
document.head.appendChild(style);
