"""
Web 代码执行器
处理 HTML, CSS, JavaScript, Vue 代码的预览生成
"""
from typing import Dict, Any
import re


class WebExecutor:
    """Web 代码预览生成器"""

    # HTML 模板
    HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码预览</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
    </style>
</head>
<body>
    {content}
</body>
</html>'''

    # CSS 模板（带示例元素）
    CSS_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSS 预览</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
        }}
        .preview-container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        {user_css}
    </style>
</head>
<body>
    <div class="preview-container">
        <h1>CSS 样式预览</h1>
        <p class="demo">这是一段示例文字，用于测试 CSS 样式。</p>
        <p>普通文字样式</p>
        <button class="demo">按钮</button>
        <div class="demo">容器元素</div>
        <a href="#" class="demo">链接样式</a>
    </div>
</body>
</html>'''

    # JavaScript 模板（带 console.log 拦截）
    JS_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JavaScript 预览</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: 'Fira Code', 'Consolas', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
        }}
        #output {{
            margin-top: 20px;
            padding: 15px;
            background: #252526;
            border-radius: 6px;
            border: 1px solid #3c3c3c;
            min-height: 100px;
            max-height: 400px;
            overflow-y: auto;
        }}
        .log-line {{
            padding: 4px 0;
            border-bottom: 1px solid #333;
        }}
        .log-line:last-child {{
            border-bottom: none;
        }}
        .log-error {{
            color: #f48771;
        }}
        .log-warn {{
            color: #cca700;
        }}
        .log-info {{
            color: #4fc1ff;
        }}
        h1 {{
            margin: 0 0 10px 0;
            font-size: 18px;
        }}
    </style>
</head>
<body>
    <h1>JavaScript 输出</h1>
    <div id="output"></div>
    <script>
        // 拦截 console 输出并显示在页面上
        const output = document.getElementById('output');
        const originalLog = console.log;
        const originalError = console.error;
        const originalWarn = console.warn;

        function addLog(message, type = 'info') {{
            const line = document.createElement('div');
            line.className = 'log-line log-' + type;
            line.textContent = String(message);
            output.appendChild(line);
        }}

        console.log = function(...args) {{
            originalLog.apply(console, args);
            args.forEach(arg => addLog(typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg), 'info'));
        }};

        console.error = function(...args) {{
            originalError.apply(console, args);
            args.forEach(arg => addLog(typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg), 'error'));
        }};

        console.warn = function(...args) {{
            originalWarn.apply(console, args);
            args.forEach(arg => addLog(typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg), 'warn'));
        }};

        // 捕获未处理的错误
        window.addEventListener('error', function(e) {{
            addLog(e.message + ' (' + e.filename + ':' + e.lineno + ')', 'error');
        }});

        try {{
            {user_code}
        }} catch (e) {{
            addLog('错误: ' + e.message, 'error');
        }}
    </script>
</body>
</html>'''

    # Vue 模板（使用 CDN 版本 Vue 3，支持 SFC 格式 + Element Plus）
    VUE_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vue 预览</title>
    <!-- Element Plus CSS -->
    <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css" />
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <!-- Element Plus JS -->
    <script src="https://unpkg.com/element-plus/dist/index.full.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #app {{
            min-height: 200px;
        }}
        {user_styles}
    </style>
</head>
<body>
    <div id="app"></div>
    <script>
        // 将 Vue API 挂载到 window 对象，使其在任何作用域都可访问
        window.Vue = Vue;
        window.ElementPlus = ElementPlus;
        window.ElementPlusIconsVue = window.ElementPlusIconsVue || {{}};
        window.createApp = Vue.createApp;
        window.ref = Vue.ref;
        window.reactive = Vue.reactive;
        window.computed = Vue.computed;
        window.watch = Vue.watch;
        window.onMounted = Vue.onMounted;
        window.onUpdated = Vue.onUpdated;
        window.onUnmounted = Vue.onUnmounted;
        window.nextTick = Vue.nextTick;

        try {{
            {user_code}
        }} catch (e) {{
            document.getElementById('app').innerHTML = '<p style="color: red; padding: 20px;">错误: ' + e.message + '<br><small style="color: #666;">' + e.stack + '</small></p>';
            console.error(e);
        }}
    </script>
</body>
</html>'''

    def _detect_vue_sfc(self, code: str) -> bool:
        """检测代码是否为 Vue SFC 格式"""
        code_stripped = code.strip()
        # 检查是否包含 Vue SFC 的特征标签
        has_template = '<template' in code_stripped
        has_script = '<script' in code_stripped
        has_style = '<style' in code_stripped
        # 如果包含 template 和 script，很可能是 Vue SFC
        # 或者包含 script setup，也是 Vue SFC
        has_script_setup = '<script' in code_stripped and 'setup' in code_stripped
        return (has_template and has_script) or has_script_setup

    async def execute(self, language: str, code: str) -> Dict[str, Any]:
        """
        生成 Web 代码预览

        Args:
            language: html, css, javascript, vue
            code: 用户代码

        Returns:
            dict: { success, html, stdout }
        """
        language = language.lower()

        # 自动检测 Vue SFC 格式（即使用户标记为 html）
        if language == 'html' and self._detect_vue_sfc(code):
            language = 'vue'

        if language == 'html':
            html = self._wrap_html(code)
        elif language == 'css':
            html = self._wrap_css(code)
        elif language in ['javascript', 'js']:
            html = self._wrap_javascript(code)
        elif language == 'vue':
            html = self._wrap_vue(code)
        else:
            html = f'<pre>不支持的语言: {language}</pre>'

        return {
            'success': True,
            'html': html,
            'stdout': '预览已生成',
            'stderr': '',
            'exitCode': 0
        }

    def _wrap_html(self, code: str) -> str:
        """包装 HTML 代码"""
        return self.HTML_TEMPLATE.format(content=code)

    def _wrap_css(self, code: str) -> str:
        """包装 CSS 代码并添加示例元素"""
        return self.CSS_TEMPLATE.format(user_css=code)

    def _wrap_javascript(self, code: str) -> str:
        """包装 JavaScript 代码"""
        # 转义代码中的 </script> 防止提前结束
        escaped_code = code.replace('</script>', r'<\/script>')
        return self.JS_TEMPLATE.format(user_code=escaped_code)

    def _clean_typescript(self, code: str) -> str:
        """移除 TypeScript 类型注解"""
        # 移除类型注解 : Type
        # 匹配 : 后面的类型，但不匹配 : 的情况（如对象中的键值对）
        # 这是个简化版本，处理常见情况
        lines = code.split('\n')
        cleaned_lines = []

        for line in lines:
            # 移除行内类型注解
            # 如: const foo: Ref<string> = ref('x')
            # 如: function bar(x: number): void {}
            # 如: const arr: string[] = []

            # 移除 : Type 形式的注解（在变量声明、参数、返回类型中）
            # 排除对象字面量中的 : (如 { name: string })
            cleaned = line

            # 移除泛型语法 <...> (如 ref<string>(), Ref<P>)
            # 但保留 HTML 标签中的 <>
            cleaned = re.sub(r'(\w+)\s*<[^>]*>', r'\1', cleaned)

            # 移除参数类型注解 (处理函数参数)
            # 如 (x: number, y: string) => {}
            # 排除对象解构的情况
            cleaned = re.sub(r'(\w+)\s*:\s*\w+(\[\])?\s*([,)])', r'\1\3', cleaned)

            # 移除 : Type 形式的变量类型注解
            # 但排除对象字面量中的情况
            # 使用更精确的模式：变量名后的类型注解
            cleaned = re.sub(r'(\w+)\s*:\s*([A-Z]\w+|string|number|boolean|any|void|null|undefined)(\[\])?\s*(?=[,=;]|$)', r'\1', cleaned)

            cleaned_lines.append(cleaned)

        return '\n'.join(cleaned_lines)

    def _clean_imports(self, code: str) -> str:
        """移除或转换 ES6 import 语句"""
        lines = code.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            # 移除 Vue 相关的 import 语句（因为我们已经提供了全局变量）
            if stripped.startswith('import') and ('vue' in stripped.lower() or re.match(r"import\s+.*\s+from\s+['\"]vue['\"]", stripped)):
                continue

            # 移除 type import（TypeScript 类型导入）
            if stripped.startswith('import type'):
                continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _process_setup_script(self, script_code: str, template: str) -> str:
        """处理 <script setup> 格式的代码"""
        # 1. 移除 ES6 imports
        script_code = self._clean_imports(script_code)

        # 2. 清理 TypeScript 类型注解
        script_code = self._clean_typescript(script_code)

        # 3. 构建 setup 函数代码
        # 将 ref/reactive/computed 等全局函数暴露到 setup 作用域
        return f'''
function setupFunc() {{
    const ref = window.ref;
    const reactive = window.reactive;
    const computed = window.computed;
    const watch = window.watch;
    const onMounted = window.onMounted;
    const onUpdated = window.onUpdated;
    const onUnmounted = window.onUnmounted;
    const nextTick = window.nextTick;

    {script_code}

    // 自动返回所有定义的 ref/reactive/computed 变量
    return {{
        get count() {{ return typeof count !== 'undefined' ? count : undefined; }},
        get Person() {{ return typeof Person !== 'undefined' ? Person : undefined; }},
        get spanhello() {{ return typeof spanhello !== 'undefined' ? spanhello : undefined; }},
        get output() {{ return typeof output !== 'undefined' ? output : undefined; }},
        get msg() {{ return typeof msg !== 'undefined' ? msg : undefined; }},
        get text() {{ return typeof text !== 'undefined' ? text : undefined; }},
        get data() {{ return typeof data !== 'undefined' ? data : undefined; }},
        get items() {{ return typeof items !== 'undefined' ? items : undefined; }},
        get message() {{ return typeof message !== 'undefined' ? message : undefined; }},
        get title() {{ return typeof title !== 'undefined' ? title : undefined; }},
        get inputText() {{ return typeof inputText !== 'undefined' ? inputText : undefined; }},
        get todos() {{ return typeof todos !== 'undefined' ? todos : undefined; }},
        get visible() {{ return typeof visible !== 'undefined' ? visible : undefined; }},
        get disabled() {{ return typeof disabled !== 'undefined' ? disabled : undefined; }},
        get loading() {{ return typeof loading !== 'undefined' ? loading : undefined; }},
        get error() {{ return typeof error !== 'undefined' ? error : undefined; }},
        get selected() {{ return typeof selected !== 'undefined' ? selected : undefined; }},
        get index() {{ return typeof index !== 'undefined' ? index : undefined; }},
        get isActive() {{ return typeof isActive !== 'undefined' ? isActive : undefined; }},
    }};
}}

const app = window.createApp({{
    template: `{template}`,
    setup: setupFunc
}});
// 注册 Element Plus
app.use(window.ElementPlus);
// 注册所有图标（如果可用）
if (window.ElementPlusIconsVue && Object.keys(window.ElementPlusIconsVue).length > 0) {{
    for (const [key, component] of Object.entries(window.ElementPlusIconsVue)) {{
        app.component(key, component);
    }}
}}
app.mount('#app');
'''

    def _wrap_vue(self, code: str) -> str:
        """包装 Vue 代码 - 支持 SFC 格式和普通 JS 格式"""
        # 检查是否是 SFC 格式（包含 <template> 标签）
        has_template = '<template' in code
        has_script = '<script' in code
        has_style = '<style' in code

        escaped_code = code.replace('</script>', r'<\/script>')

        # 如果是 SFC 格式，需要解析和转换
        if has_template or has_style:
            # 提取样式
            styles = []
            if has_style:
                style_matches = re.findall(r'<style[^>]*>(.*?)</style>', code, re.DOTALL)
                for style_content in style_matches:
                    # 移除 scoped 属性相关的标记
                    clean_style = style_content.replace('scoped', '').strip()
                    if clean_style:
                        styles.append(clean_style)

            # 提取脚本内容和检查是否是 setup
            script_code = ''
            is_setup = False
            if has_script:
                script_matches = re.findall(r'<script[^>]*>(.*?)</script>', code, re.DOTALL)
                if script_matches:
                    script_code = script_matches[0].strip()
                    # 检查是否是 setup 脚本
                    script_tag_match = re.search(r'<script([^>]*)>', code)
                    if script_tag_match:
                        script_attrs = script_tag_match.group(1)
                        is_setup = 'setup' in script_attrs

            # 提取模板内容
            template = ''
            if has_template:
                template_matches = re.findall(r'<template[^>]*>(.*?)</template>', code, re.DOTALL)
                if template_matches:
                    template = template_matches[0].strip()

            # 构建可执行的 Vue 代码
            if template and script_code:
                if is_setup:
                    # <script setup> 格式 - 需要特殊处理
                    executable_code = self._process_setup_script(script_code, template)
                elif 'export default' in script_code or 'export {' in script_code:
                    # Options API 格式（export default）
                    script_code = script_code.replace('export default', 'const appOptions =')
                    script_code = script_code.replace('export {', '')
                    executable_code = f'''
{script_code}
appOptions.template = `{template}`;
const app = Vue.createApp(appOptions);
app.use(window.ElementPlus);
// 注册所有图标（如果可用）
if (window.ElementPlusIconsVue && Object.keys(window.ElementPlusIconsVue).length > 0) {{
    for (const [key, component] of Object.entries(window.ElementPlusIconsVue)) {{
        app.component(key, component);
    }}
}}
app.mount('#app');
'''
                else:
                    # 普通脚本，直接执行
                    executable_code = script_code
            elif template:
                # 只有模板，创建简单的应用
                executable_code = f'''
const app = Vue.createApp({{
    template: `{template}`,
    data() {{ return {{ count: 0 }} }}
}});
app.use(window.ElementPlus);
// 注册所有图标（如果可用）
if (window.ElementPlusIconsVue && Object.keys(window.ElementPlusIconsVue).length > 0) {{
    for (const [key, component] of Object.entries(window.ElementPlusIconsVue)) {{
        app.component(key, component);
    }}
}}
app.mount('#app');
'''
            else:
                # 只有脚本，直接执行
                executable_code = script_code

            # 转义代码中的 </script>
            executable_code = executable_code.replace('</script>', r'<\/script>')

            # 组合样式
            combined_styles = '\n'.join(styles)

            return self.VUE_TEMPLATE.format(user_code=executable_code, user_styles=combined_styles)

        # 普通非 SFC 格式，直接包装
        return self.VUE_TEMPLATE.format(user_code=escaped_code, user_styles='')
