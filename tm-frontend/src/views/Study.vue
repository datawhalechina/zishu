<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLoginStore } from '../store'
import { fetchCourseDetailAPI, fetchTutorialContentAPI, reportStudyTimeAPI, syncStudyTimeAPI } from '../request/tutorial/api'
import { addStudyTimeAPI } from '../request/inno/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import hljs from 'highlight.js'
import { marked } from 'marked'
import 'highlight.js/styles/atom-one-light.css'
import CodeBlock from '@/components/code-editor/CodeBlock.vue'
import { getDefaultLanguageForCourse } from '@/utils/languageMapping'

// 配置 marked 选项
marked.setOptions({
  breaks: true,  // 支持单个换行符转换为 <br>
  gfm: true,     // 启用 GitHub 风格 Markdown
})

// 配置 marked 代码高亮
marked.setOptions({
  highlight: function(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  }
})

// 注册常用语言（如果不存在则使用 plaintext）
hljs.registerLanguage('vue', () => ({ inherit: hljs['xml'] } as any))
hljs.registerLanguage('javascript', () => hljs.getLanguage('js') || hljs.getLanguage('javascript') || { aliases: ['js'] } as any)
hljs.registerLanguage('typescript', () => hljs.getLanguage('ts') || hljs.getLanguage('typescript') || { aliases: ['ts'] } as any)
hljs.registerLanguage('html', () => hljs.getLanguage('xml') || { aliases: ['html'] } as any)
hljs.registerLanguage('css', () => hljs.getLanguage('css') || { aliases: ['css'] } as any)
hljs.registerLanguage('python', () => hljs.getLanguage('py') || hljs.getLanguage('python') || { aliases: ['py'] } as any)
hljs.registerLanguage('bash', () => hljs.getLanguage('sh') || hljs.getLanguage('bash') || { aliases: ['sh'] } as any)
hljs.registerLanguage('json', () => hljs.getLanguage('json') || { aliases: ['json'] } as any)

document.title = '学习'

interface Chapter {
  name: string
  lessons: Array<{
    title: string
    path: string
    duration: number
  }>
}

interface Course {
  name: string
  path: string
  total_lessons: number
  chapters: Chapter[]
}

const route = useRoute()
const router = useRouter()
const loginstate = useLoginStore()

const loading = ref(false)
const course = ref<Course | null>(null)
const currentContent = ref('')
const currentPath = ref('')
const currentTitle = ref('')
const currentChapter = ref('')
const studyTimer = ref(0)
const timerInterval = ref<number | null>(null)
const showReportDialog = ref(false)
const reportDuration = ref(30)
const completedLessons = ref<Set<string>>(new Set())

// 代码块数据接口
interface CodeBlockData {
  id: string
  code: string
  language: string
}

// 解析后的内容接口
interface ParsedContent {
  html: string
  codeBlocks: CodeBlockData[]
}

// 获取课程详情
const fetchCourse = async () => {
  const courseName = route.query.course as string
  if (!courseName) return

  loading.value = true
  try {
    const res = await fetchCourseDetailAPI(courseName)
    if (res.code === 200) {
      course.value = res.data

      // 如果有指定章节，跳转到章节第一课
      const chapterName = route.query.chapter as string
      if (chapterName) {
        currentChapter.value = chapterName
        const chapter = course.value.chapters.find(c => c.name === chapterName)
        if (chapter && chapter.lessons.length > 0) {
          const firstLesson = chapter.lessons[0]
          loadLesson(firstLesson.path, firstLesson.title, chapter.name)
        }
      }
    }
  } catch (error) {
    ElMessage.error('获取课程失败')
  } finally {
    loading.value = false
  }
}

// 加载课程内容
const loadLesson = async (path: string, title: string, chapter: string) => {
  if (!path) return

  loading.value = true
  try {
    const res = await fetchTutorialContentAPI({ path })
    if (res.code === 200) {
      currentContent.value = res.data.content
      currentPath.value = path
      currentTitle.value = title
      currentChapter.value = chapter
      document.title = title

      // 开始计时
      startTimer()
    }
  } catch (error) {
    ElMessage.error('加载内容失败')
  } finally {
    loading.value = false
  }
}

// 开始学习计时
const startTimer = () => {
  stopTimer()
  studyTimer.value = 0
  timerInterval.value = window.setInterval(() => {
    studyTimer.value++
  }, 1000)
}

// 停止计时
const stopTimer = () => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

// 格式化时间
const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 上一课
const prevLesson = () => {
  if (!course.value) return

  let allLessons: Array<{ path: string; title: string; chapter: string }> = []
  for (const ch of course.value.chapters) {
    for (const lesson of ch.lessons) {
      allLessons.push({ path: lesson.path, title: lesson.title, chapter: ch.name })
    }
  }

  const currentIndex = allLessons.findIndex(l => l.path === currentPath.value)
  if (currentIndex > 0) {
    const prev = allLessons[currentIndex - 1]
    loadLesson(prev.path, prev.title, prev.chapter)
  } else {
    ElMessage.info('已经是第一课了')
  }
}

// 下一课
const nextLesson = () => {
  if (!course.value) return

  let allLessons: Array<{ path: string; title: string; chapter: string }> = []
  for (const ch of course.value.chapters) {
    for (const lesson of ch.lessons) {
      allLessons.push({ path: lesson.path, title: lesson.title, chapter: ch.name })
    }
  }

  const currentIndex = allLessons.findIndex(l => l.path === currentPath.value)
  if (currentIndex < allLessons.length - 1) {
    const next = allLessons[currentIndex + 1]
    loadLesson(next.path, next.title, next.chapter)
  } else {
    ElMessage.info('已经是最后一课了')
  }
}

// 完成学习，申报时间
const finishStudy = async () => {
  if (!course.value) return

  stopTimer()

  // 标记为已完成
  completedLessons.value.add(currentPath.value)

  // 弹出申报对话框
  reportDuration.value = Math.ceil(studyTimer.value / 60) || 30
  showReportDialog.value = true
}

// 提交学习时间申报
const submitReport = async () => {
  if (!loginstate.id) {
    ElMessage.warning('请先登录')
    return
  }

  // 确保 user_id 是数字类型
  const userId = Number(loginstate.id)

  try {
    await ElMessageBox.confirm(
      `确认申报学习时间 ${reportDuration.value} 分钟？\n申报后将同步到时间管理页面。`,
      '申报学习时间',
      {
        confirmButtonText: '确认申报',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    // 1. 申报学习时间
    const res = await reportStudyTimeAPI({
      user_id: userId,
      course_name: course.value?.name || '',
      lesson_title: currentTitle.value,
      duration: reportDuration.value
    })

    if (res.code === 200) {
      // 2. 同步到时间管理
      const now = new Date()
      const dateString = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '/')

      // 构建时间管理记录
      const studyRecord = [
        "",  // 编号
        `学习-${course.value?.name || ''}`,  // 主题
        reportDuration.value,  // 目标用时
        currentTitle.value,  // 分拆事项
        reportDuration.value,  // 计划用时
        "",  // 开始时间
        "",  // 结束时间
        reportDuration.value,  // 实际用时
        dateString  // 日期
      ]

      await addStudyTimeAPI(userId, [studyRecord])

      ElMessage.success('申报成功！时间已同步到时间管理')
      showReportDialog.value = false

      // 询问是否跳转到时间管理页面查看
      try {
        await ElMessageBox.confirm(
          '学习时间已申报成功，是否前往时间管理页面查看？',
          '跳转提示',
          {
            confirmButtonText: '前往查看',
            cancelButtonText: '留在此页',
            type: 'success'
          }
        )
        router.push('/manager')
      } catch {
        // 用户选择留在当前页面
      }
    }
  } catch {
    // 用户取消
  }
}

// 页面离开时自动申报
onMounted(() => {
  fetchCourse()
})

onUnmounted(() => {
  stopTimer()
})

// 路由变化时重新加载
watch(() => route.query, () => {
  fetchCourse()
})

// 使用 marked 库渲染 Markdown，但先提取代码块用于 CodeBlock 组件
const renderMarkdown = (content: string): ParsedContent => {
  if (!content) return { html: '', codeBlocks: [] }

  // 先处理代码块，提取语言类型和代码
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
  const codeBlocks: CodeBlockData[] = []
  let blockIndex = 0

  // 替换代码块为占位符
  let processedContent = content.replace(codeBlockRegex, (match, lang, code) => {
    const safeLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
    const blockId = `code-block-${blockIndex++}`

    codeBlocks.push({
      id: blockId,
      code: code.trim(),
      language: safeLang
    })

    return `<!--CODE_BLOCK:${blockId}-->`
  })

  // 使用 marked 渲染其余的 Markdown 内容
  const html = marked.parse(processedContent) as string

  return { html, codeBlocks }
}

// 解析当前内容为 HTML 和代码块数据
const parsedContent = computed((): ParsedContent => {
  if (!currentContent.value) return { html: '', codeBlocks: [] }
  return renderMarkdown(currentContent.value)
})

// 根据课程名称获取默认语言
const courseDefaultLanguage = computed(() => {
  return getDefaultLanguageForCourse(course.value?.name || '')
})
</script>

<template>
  <div class="study-container">
    <!-- 左侧课程大纲 -->
    <div class="sidebar">
      <el-card class="sidebar-card">
        <template #header>
          <div class="sidebar-header">
            <el-page-header @back="$router.back()" title="返回">
              <template #content>
                <span class="sidebar-title">{{ course?.name || '课程' }}</span>
              </template>
            </el-page-header>
          </div>
        </template>

        <div class="chapter-list" v-if="course">
          <div
            v-for="chapter in course.chapters"
            :key="chapter.name"
            class="chapter-block"
          >
            <div class="chapter-name">
              <el-icon><FolderOpened /></el-icon>
              {{ chapter.name }}
            </div>
            <div class="lesson-grid">
              <div
                v-for="lesson in chapter.lessons"
                :key="lesson.path"
                class="lesson-btn"
                :class="{ active: currentPath === lesson.path, completed: completedLessons.has(lesson.path) }"
                @click="loadLesson(lesson.path, lesson.title, chapter.name)"
              >
                <el-icon v-if="completedLessons.has(lesson.path)" class="check-icon"><CircleCheck /></el-icon>
                <span class="lesson-name">{{ lesson.title }}</span>
                <el-tag type="info" size="small">{{ lesson.duration }}分</el-tag>
              </div>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 右侧学习内容 -->
    <div class="main-content">
      <el-card class="content-card" v-loading="loading">
        <template #header>
          <div class="content-header">
            <div class="header-left">
              <el-page-header @back="$router.back()" title="返回课程">
                <template #content>
                  <span class="content-title">{{ currentTitle || '选择课程开始学习' }}</span>
                </template>
                <template #extra>
                  <div class="timer-display">
                    <el-icon><Clock /></el-icon>
                    {{ formatTime(studyTimer) }}
                  </div>
                </template>
              </el-page-header>
            </div>
            <div class="header-actions">
              <el-button @click="prevLesson">
                <el-icon><ArrowLeft /></el-icon>上一课
              </el-button>
              <el-button type="primary" @click="finishStudy" :disabled="!currentPath">
                <el-icon><Check /></el-icon>完成学习
              </el-button>
              <el-button @click="nextLesson">
                下一课<el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </div>
        </template>

        <div v-if="currentContent" class="markdown-content">
  <!-- 渲染普通 HTML 内容 -->
  <div v-html="parsedContent.html"></div>
  <!-- 渲染代码块组件 -->
  <CodeBlock
    v-for="block in parsedContent.codeBlocks"
    :key="`${block.id}-${currentPath}`"
    :code="block.code"
    :language="block.language"
    :course-default-language="courseDefaultLanguage"
  />
</div>
        <el-empty v-else-if="!loading" description="请从左侧选择课程开始学习">
          <el-button type="primary" @click="router.push('/courses')">浏览课程</el-button>
        </el-empty>
      </el-card>
    </div>

    <!-- 申报学习时间对话框 -->
    <el-dialog
      v-model="showReportDialog"
      title="申报学习时间"
      width="400px"
      center
    >
      <el-form label-position="top">
        <el-form-item label="课程名称">
          <el-input :value="course?.name" disabled />
        </el-form-item>
        <el-form-item label="课时名称">
          <el-input :value="currentTitle" disabled />
        </el-form-item>
        <el-form-item label="学习时长（分钟）">
          <el-input-number
            v-model="reportDuration"
            :min="1"
            :max="300"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
        >
          申报后，学习时间将同步到时间管理页面。
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="showReportDialog = false">取消</el-button>
        <el-button type="primary" @click="submitReport">确认申报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import {
  FolderOpened, CircleCheck, Clock, ArrowLeft, ArrowRight, Check
} from '@element-plus/icons-vue'
</script>

<style scoped>
.study-container {
  display: flex;
  gap: 20px;
  padding: 20px;
  height: calc(100vh - 100px);
}

.sidebar {
  width: 300px;
  flex-shrink: 0;
  overflow-y: auto;
}

.sidebar-card {
  height: 100%;
}

.sidebar-header {
  padding: 4px 0;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-block {
  margin-bottom: 8px;
}

.chapter-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
}

.lesson-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.lesson-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.lesson-btn:hover {
  background: #f5f7fa;
}

.lesson-btn.active {
  background: #ecf5ff;
  color: #409eff;
}

.lesson-btn.completed {
  color: #67c23a;
}

.check-icon {
  color: #67c23a;
}

.lesson-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.content-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  flex: 1;
}

.content-title {
  font-size: 16px;
  font-weight: 600;
}

.timer-display {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  font-weight: 600;
  color: #409eff;
  margin-left: 16px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.markdown-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  line-height: 1.8;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  color: #303133;
  margin: 16px 0 12px;
}

.markdown-content :deep(p) {
  margin: 12px 0;
  color: #606266;
}

.markdown-content :deep(li) {
  margin: 8px 0;
  color: #606266;
}

.markdown-content :deep(blockquote) {
  margin: 16px 0;
  padding: 10px 16px;
  background: #f5f7fa;
  border-left: 4px solid #409eff;
  color: #606266;
}

.markdown-content :deep(pre) {
  margin: 16px 0;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 6px;
  overflow-x: auto;
  max-width: 100%;
}

.markdown-content :deep(pre code) {
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: #24292e;
  white-space: pre;
  word-wrap: normal;
  word-break: normal;
}

.markdown-content :deep(.inline-code) {
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  color: #d73a49;
}

.markdown-content :deep(.code-block) {
  background: #f5f7fa;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.markdown-content :deep(hr) {
  margin: 24px 0;
  border: none;
  border-top: 1px solid #ebeef5;
}
</style>
