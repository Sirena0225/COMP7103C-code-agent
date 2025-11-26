/**
 * arXiv 论文浏览器 - 前端交互脚本
 */

document.addEventListener('DOMContentLoaded', function() {
    initSearchHighlight();
    initSmoothScroll();
    initKeyboardShortcuts();
    initLazyLoading();
});

/**
 * 搜索关键词高亮
 */
function initSearchHighlight() {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (query && query.trim()) {
        const keywords = query.trim().split(/\s+/);
        const paperCards = document.querySelectorAll('.paper-card');
        
        paperCards.forEach(card => {
            const title = card.querySelector('.paper-title');
            const summary = card.querySelector('.paper-summary');
            
            if (title) highlightText(title, keywords);
            if (summary) highlightText(summary, keywords);
        });
    }
}

/**
 * 高亮文本中的关键词
 */
function highlightText(element, keywords) {
    let html = element.innerHTML;
    
    keywords.forEach(keyword => {
        if (keyword.length > 1) {
            const regex = new RegExp(`(${escapeRegex(keyword)})`, 'gi');
            html = html.replace(regex, '<mark class="highlight">$1</mark>');
        }
    });
    
    element.innerHTML = html;
}

/**
 * 转义正则特殊字符
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 平滑滚动
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * 键盘快捷键
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K: 聚焦搜索框
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input, .search-input-large');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Esc: 取消搜索框焦点
        if (e.key === 'Escape') {
            document.activeElement.blur();
        }
        
        // 首页快捷键
        if (e.key === 'h' && !isTyping()) {
            window.location.href = '/';
        }
    });
}

/**
 * 检查是否在输入状态
 */
function isTyping() {
    const activeElement = document.activeElement;
    const tagName = activeElement.tagName.toLowerCase();
    return tagName === 'input' || tagName === 'textarea' || activeElement.isContentEditable;
}

/**
 * 懒加载初始化
 */
function initLazyLoading() {
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px',
            threshold: 0.1
        });
        
        document.querySelectorAll('.paper-card').forEach(card => {
            observer.observe(card);
        });
    }
}

/**
 * 复制到剪贴板（通用函数）
 */
async function copyToClipboard(text, buttonElement) {
    try {
        await navigator.clipboard.writeText(text);
        
        if (buttonElement) {
            const originalText = buttonElement.textContent;
            buttonElement.textContent = '✅ 已复制!';
            buttonElement.classList.add('copied');
            
            setTimeout(() => {
                buttonElement.textContent = originalText;
                buttonElement.classList.remove('copied');
            }, 2000);
        }
        
        return true;
    } catch (err) {
        console.error('复制失败:', err);
        
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            if (buttonElement) {
                buttonElement.textContent = '✅ 已复制!';
                setTimeout(() => {
                    buttonElement.textContent = '📋 一键复制';
                }, 2000);
            }
        } catch (e) {
            console.error('降级复制也失败:', e);
        }
        
        document.body.removeChild(textarea);
        return false;
    }
}

/**
 * 复制 BibTeX（论文详情页使用）
 */
function copyBibtex() {
    const bibtexContent = document.getElementById('bibtex-content');
    const btn = document.getElementById('copy-btn');
    
    if (bibtexContent && btn) {
        copyToClipboard(bibtexContent.textContent, btn);
    }
}

/**
 * 格式化日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('zh-CN', options);
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === 'success' ? '#3fb950' : type === 'error' ? '#f85149' : '#58a6ff'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        transform: translateY(100px);
        opacity: 0;
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // 动画显示
    requestAnimationFrame(() => {
        notification.style.transform = 'translateY(0)';
        notification.style.opacity = '1';
    });
    
    // 自动消失
    setTimeout(() => {
        notification.style.transform = 'translateY(100px)';
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * 防抖函数
 */
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

/**
 * 搜索建议（可扩展）
 */
const searchSuggestions = debounce(function(input) {
    const query = input.value.trim();
    if (query.length < 2) return;
    
    // 这里可以添加 AJAX 请求获取搜索建议
    console.log('搜索建议:', query);
}, 300);

// 绑定搜索输入事件
document.querySelectorAll('.search-input, .search-input-large').forEach(input => {
    input.addEventListener('input', () => searchSuggestions(input));
});

/**
 * 回到顶部功能
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 显示/隐藏回到顶部按钮
window.addEventListener('scroll', debounce(function() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    let backToTopBtn = document.getElementById('back-to-top');
    
    if (scrollTop > 500) {
        if (!backToTopBtn) {
            backToTopBtn = document.createElement('button');
            backToTopBtn.id = 'back-to-top';
            backToTopBtn.innerHTML = '⬆️';
            backToTopBtn.onclick = scrollToTop;
            backToTopBtn.style.cssText = `
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: #388bfd;
                color: white;
                border: none;
                cursor: pointer;
                font-size: 1.2rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 1000;
                transition: all 0.3s ease;
                opacity: 0;
                transform: scale(0.8);
            `;
            document.body.appendChild(backToTopBtn);
            
            requestAnimationFrame(() => {
                backToTopBtn.style.opacity = '1';
                backToTopBtn.style.transform = 'scale(1)';
            });
        }
    } else if (backToTopBtn) {
        backToTopBtn.style.opacity = '0';
        backToTopBtn.style.transform = 'scale(0.8)';
        setTimeout(() => backToTopBtn.remove(), 300);
    }
}, 100));

console.log('🚀 arXiv 论文浏览器已加载');
console.log('💡 提示: 使用 Ctrl+K 快速聚焦搜索框');

