<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCoursesAPI } from '../request/tutorial/api'
import { ElMessage } from 'element-plus'

document.title = '课程列表'

interface Lesson {
  title: string
  path: string
  duration: number
}

interface Chapter {
  name: string
  lessons: Lesson[]
}

interface Course {
  name: string
  path: string
  total_lessons: number
  total_duration: number
  chapters: Chapter[]
}

const router = useRouter()
const loading = ref(false)
const courses = ref<Course[]>([])
const expandedCourses = ref<Set<string>>(new Set())
const searchKeyword = ref('')

const filteredCourses = computed(() => {
  if (!searchKeyword.value.trim()) return courses.value
  const keyword = searchKeyword.value.trim().toLowerCase()
  return courses.value.filter(course => {
    const courseMatch = course.name.toLowerCase().includes(keyword)
    const chapterMatch = course.chapters.some(ch =>
      ch.name.toLowerCase().includes(keyword) ||
      ch.lessons.some(l => l.title.toLowerCase().includes(keyword))
    )
    return courseMatch || chapterMatch
  })
})

const getCourseIcon = (name: string) => {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('fastapi')) return 'Connection'
  if (nameLower.includes('element') || nameLower.includes('vue')) return 'ElementPlus'
  if (nameLower.includes('excel') || nameLower.includes('xlsx')) return 'Excel'
  if (nameLower.includes('pdf')) return 'Document'
  if (nameLower.includes('word') || nameLower.includes('doc')) return 'DocumentCopy'
  if (nameLower.includes('python')) return 'Platform'
  if (nameLower.includes('auto') || nameLower.includes('automation')) return 'MagicStick'
  if (nameLower.includes('css') || nameLower.includes('style')) return 'Brush'
  if (nameLower.includes('typescript') || nameLower.includes('ts')) return 'Code'
  if (nameLower.includes('ppt') || nameLower.includes('powerpoint') || nameLower.includes('演示')) return 'Presentation'
  if (nameLower.includes('time') || nameLower.includes('时间')) return 'Timer'
  if (nameLower.includes('knowledge') || nameLower.includes('知识') || nameLower.includes('知识产权')) return 'Opportunity'
  if (nameLower.includes('compress') || nameLower.includes('zip') || nameLower.includes('压缩')) return 'FolderZipped'
  if (nameLower.includes('keyboard') || nameLower.includes('mouse') || nameLower.includes('键鼠')) return 'Mouse'
  if (nameLower.includes('study') || nameLower.includes('学习')) return 'Reading'
  return 'Collection'
}

const getCourseColor = (name: string) => {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('fastapi')) return '#009688'
  if (nameLower.includes('element') || nameLower.includes('vue')) return '#409EFF'
  if (nameLower.includes('excel') || nameLower.includes('xlsx')) return '#217346'
  if (nameLower.includes('pdf')) return '#F56C6C'
  if (nameLower.includes('word') || nameLower.includes('doc')) return '#2B579A'
  if (nameLower.includes('python')) return '#3776AB'
  if (nameLower.includes('auto') || nameLower.includes('automation')) return '#E3F2FD'
  if (nameLower.includes('css') || nameLower.includes('style')) return '#9C27B0'
  if (nameLower.includes('typescript') || nameLower.includes('ts')) return '#3178C6'
  if (nameLower.includes('ppt') || nameLower.includes('powerpoint') || nameLower.includes('演示')) return '#D24726'
  if (nameLower.includes('time') || nameLower.includes('时间')) return '#FF9800'
  if (nameLower.includes('knowledge') || nameLower.includes('知识') || nameLower.includes('知识产权')) return '#4CAF50'
  if (nameLower.includes('compress') || nameLower.includes('zip') || nameLower.includes('压缩')) return '#795548'
  if (nameLower.includes('keyboard') || nameLower.includes('mouse') || nameLower.includes('键鼠')) return '#607D8B'
  return '#909399'
}

const formatDuration = (minutes: number) => {
  if (minutes < 60) return `${minutes}分钟`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`
}

const toggleCourse = (coursePath: string) => {
  if (expandedCourses.value.has(coursePath)) {
    expandedCourses.value.delete(coursePath)
  } else {
    expandedCourses.value.add(coursePath)
  }
}

const fetchCourses = async () => {
  loading.value = true
  try {
    const res = await fetchCoursesAPI()
    if (res.code === 200) {
      courses.value = res.data
      // 默认展开前2个课程
      courses.value.slice(0, 2).forEach(c => expandedCourses.value.add(c.path))
    }
  } catch (error) {
    ElMessage.error('获取课程列表失败')
  } finally {
    loading.value = false
  }
}

const goToStudy = (course: Course, chapter?: Chapter, lesson?: Lesson) => {
  if (lesson) {
    router.push({
      path: '/study',
      query: {
        course: course.path,
        chapter: chapter?.name || '',
        path: lesson.path,
        title: lesson.title
      }
    })
  } else if (chapter) {
    router.push({
      path: '/study',
      query: {
        course: course.path,
        chapter: chapter.name
      }
    })
  } else {
    router.push({
      path: '/study',
      query: { course: course.path }
    })
  }
}

onMounted(fetchCourses)
</script>

<template>
  <div class="courses-container">
    <el-card class="course-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <el-page-header @back="$router.back()" title="返回">
            <template #content>
              <span class="header-title">课程中心</span>
            </template>
          </el-page-header>
        </div>
      </template>

      <div v-if="courses.length > 0" class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索课程、章节或课时..."
          clearable
          prefix-icon="Search"
        />
      </div>

      <div v-if="filteredCourses.length === 0 && !loading" class="empty-tip">
        <el-empty :description="searchKeyword ? '未找到匹配的课程' : '暂无课程'" />
      </div>

      <div v-else class="course-tree">
        <div
          v-for="course in filteredCourses"
          :key="course.path"
          class="course-node"
        >
          <!-- 课程标题行 -->
          <div
            class="course-title-row"
            @click="toggleCourse(course.path)"
          >
            <el-icon class="expand-icon" :class="{ expanded: expandedCourses.has(course.path) }">
              <ArrowRight />
            </el-icon>
            <el-avatar
              :size="40"
              :style="{ background: getCourseColor(course.name) }"
            >
              <el-icon :size="20"><component :is="getCourseIcon(course.name)" /></el-icon>
            </el-avatar>
            <div class="course-title-info">
              <span class="course-name">{{ course.name }}</span>
              <span class="course-meta">
                {{ course.total_lessons }} 课时 · {{ formatDuration(course.total_duration) }}
              </span>
            </div>
            <el-button type="primary" size="small" @click.stop="goToStudy(course)">
              开始学习
            </el-button>
          </div>

          <!-- 章节折叠内容 -->
          <div v-if="expandedCourses.has(course.path)" class="course-children">
            <div
              v-for="(chapter, idx) in course.chapters"
              :key="chapter.name"
              class="chapter-node"
            >
              <div
                class="chapter-title-row"
                @click="goToStudy(course, chapter)"
              >
                <el-icon class="folder-icon"><FolderOpened /></el-icon>
                <span class="chapter-name">{{ chapter.name }}</span>
                <el-tag type="info" size="small">{{ chapter.lessons.length }}节</el-tag>
              </div>

              <!-- 课时列表 -->
              <div class="lesson-list">
                <div
                  v-for="lesson in chapter.lessons"
                  :key="lesson.path"
                  class="lesson-item"
                  @click="goToStudy(course, chapter, lesson)"
                >
                  <el-icon class="lesson-icon"><DocumentChecked /></el-icon>
                  <span class="lesson-title">{{ lesson.title }}</span>
                  <el-tag type="info" size="small">{{ lesson.duration }}分钟</el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script lang="ts">
import {
  Connection, ElementPlus, Excel, Document, DocumentCopy,
  Platform, MagicStick, Reading, Clock, FolderOpened,
  DocumentChecked, Brush, Code, Presentation, Timer,
  Opportunity, FolderZipped, Mouse, Collection, ArrowRight,
  Search
} from '@element-plus/icons-vue'
</script>

<style scoped>
.courses-container {
  padding: 20px;
}

.course-card {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
}

.search-bar {
  margin-bottom: 16px;
}

.empty-tip {
  padding: 40px 0;
}

.course-tree {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-node {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
}

.course-node:hover {
  border-color: #409EFF;
}

.course-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fafafa;
  cursor: pointer;
  transition: background 0.2s;
}

.course-title-row:hover {
  background: #f5f7fa;
}

.expand-icon {
  color: #909399;
  transition: transform 0.3s;
  font-size: 16px;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.course-title-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.course-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.course-meta {
  font-size: 12px;
  color: #909399;
}

.course-children {
  padding: 8px 16px 16px 48px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
}

.chapter-node {
  margin-top: 12px;
}

.chapter-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f0f2f5;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.chapter-title-row:hover {
  background: #e4e7ed;
}

.folder-icon {
  color: #E6A23C;
  font-size: 16px;
}

.chapter-name {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.lesson-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 24px;
  margin-top: 8px;
}

.lesson-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.lesson-item:hover {
  background: #ecf5ff;
}

.lesson-item:hover .lesson-title {
  color: #409EFF;
}

.lesson-icon {
  color: #409EFF;
  font-size: 14px;
}

.lesson-title {
  flex: 1;
  font-size: 13px;
  color: #606266;
  transition: color 0.2s;
}
</style>
