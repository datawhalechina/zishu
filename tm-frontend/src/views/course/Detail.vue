<script setup lang="ts">
import { useLoginStore } from "../../store";
import {getCourseAPI} from '../../request/course/api'
import {Chapter} from '../../request/course/type'
import { ref, reactive, onMounted, computed} from 'vue'
const loginstate = useLoginStore();
document.title  = "课程明细"
import { useRoute } from 'vue-router'
const tableData:Chapter[] = reactive([])
const currentData:any = reactive([])
const finishData:any = reactive([])
const route = useRoute()
const courseid = Number(route.params.id)
const userid = loginstate.id

const getCourse = async () => {
  let res = await getCourseAPI({course_id:courseid})
  console.log(res)
  course.id = res.course.id
  course.title=res.course.title
  course.director_id=res.course.director_id
  course.director_name=res.course.director_name
  course.desc=res.course.desc
  tableData.push(...res.chapters)
  document.title  = course.title
  currentData.push(...res.current)
  finishData.push(...res.finish)
}

onMounted(getCourse)

const course = reactive({
  id:0,
  title: '',
  director_name: '',
  director_id: 0,
  desc: '',
})

// 计算属性，根据截止日期返回颜色  
const deadlineColors = computed(() => {  
  return currentData.reduce((colors:any, row:any) => {  
    const deadlineDate = new Date(row.deadline); 
    const today = ref(new Date());   
    const diffMilliseconds = (deadlineDate.getTime() - (today.value as Date).getTime());
    const diffDays = diffMilliseconds / (1000 * 60 * 60 * 24);  
  
    if (diffDays == 0) {  
      colors[row.deadline] = 'orange';  
    } else if (diffDays > 0 && diffDays <= 3) {  
      colors[row.deadline] = 'blue';  
    } else if (diffDays < 0) {  
      colors[row.deadline] = 'red';  
    } else {  
      colors[row.deadline] = '';  
    }  
  
    return colors;  
  }, {} as { [key: string]: string });  
});  
  
// 函数，用于获取截止日期的颜色  
function getDeadlineColor(deadline: string) {  
  return deadlineColors.value[deadline] || '';  
}  
</script>

<template>
  <h3>{{ course.title }}</h3>
  <h5>塾主：<el-link type="primary" :href="'/user/profile/'+course.director_id" target="_blank">{{ course.director_name }}</el-link></h5>
  <h5 v-if="course.director_id==userid"><el-link type="primary" :href="'/course/edit/'+course.id" target="_blank">编辑课程</el-link></h5>
  <div>{{ course.desc }}</div>
  <el-table 
  :data="tableData" 
  stripe 
  highlight-current-row
  style="width: 100%"
  >
    <el-table-column label="章节序号" type="index" width="100" />
    <el-table-column label="章节名称" sortable >
      <template #default="scope">
        <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column prop="author_name" label="作者" sortable  />
    <el-table-column prop="period" label="学习周期" sortable  />
  </el-table>
  <h3>当前同塾</h3>
  <el-table 
  :data="currentData" 
  stripe 
  highlight-current-row
  style="width: 100%"
  >
    <el-table-column label="同塾序号" type="index" width="100" />
    <el-table-column label="塾生">
      <template #default="scope">
        <el-link v-if="scope.row.user_id" :href="'/user/profile/'+scope.row.user_id" target="_blank" type="primary">{{ scope.row.user_name }}</el-link>
        <el-link v-else type="primary"></el-link>
      </template>
    </el-table-column>
    <el-table-column label="塾师">
      <template #default="scope">
        <el-link v-if="scope.row.shushi_id" :href="'/user/profile/'+scope.row.shushi_id" target="_blank" type="primary">{{ scope.row.shushi_name }}</el-link>
        <el-link v-else type="primary"></el-link>
      </template>
    </el-table-column>
    <el-table-column prop="current_serial" label="课次" />
    <el-table-column label="截止日期">
      <template #default="scope">
        <span :class="getDeadlineColor(scope.row.deadline)">  
          {{ scope.row.deadline?scope.row.deadline.slice(0,10):'' }} 
        </span>
      </template>
    </el-table-column>
  </el-table>

  <h3>结课同塾</h3>
  <el-table 
  :data="finishData" 
  stripe 
  highlight-current-row
  style="width: 100%"
  >
    <el-table-column label="同塾序号" type="index" width="100" />
    <el-table-column label="塾生">
      <template #default="scope">
        <el-link v-if="scope.row.user_id" :href="'/user/profile/'+scope.row.user_id" target="_blank" type="primary">{{ scope.row.user_name }}</el-link>
        <el-link v-else type="primary"></el-link>
      </template>
    </el-table-column>
    <el-table-column label="塾师">
      <template #default="scope">
        <el-link v-if="scope.row.shushi_id" :href="'/user/profile/'+scope.row.shushi_id" target="_blank" type="primary">{{ scope.row.shushi_name }}</el-link>
        <el-link v-else type="primary"></el-link>
      </template>
    </el-table-column>
    <el-table-column label="结课日期">
      <template #default="scope">
        <span :class="getDeadlineColor(scope.row.finish_date)">  
          {{ scope.row.finish_date?scope.row.finish_date.slice(0,10):'' }} 
        </span>
      </template>
    </el-table-column>
  </el-table>
</template>

<style lang="scss" scoped>
.orange {  
  color: orange;  
}  
.blue {  
  color: blue;  
}  
.red {  
  color: red;  
}  
</style>