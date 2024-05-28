<script setup lang="ts">
import {fetchCourseAPI, selectCourseAPI, fetchCurrentSelectionAPI, reportLearnAPI} from '../../request/course/api'
import { ref, reactive, onMounted, computed } from 'vue'
import router from '../../router'
import { useLoginStore } from "../../store";
import { ElMessage } from 'element-plus';
document.title = "学习"
const loginstate = useLoginStore();
const tableData:any = reactive([])
const getAllCourse = async () => {
  let res = await fetchCourseAPI()
  //console.log(res)
  tableData.push(...res)
}
onMounted(getAllCourse)

const currentTableData:any = reactive([])
const currentSelections:any = reactive([])
const getCurrentSelection = async () => {
  let res2 = await fetchCurrentSelectionAPI()
  currentTableData.push(...res2)
  res2.forEach((course:any) => {
    currentSelections.push(course.course_id)
  })
}
onMounted(getCurrentSelection)

function isFloat(str:string) {
    // 定义浮点数的正则表达式
    var reg = /^[-+]?(\d+)?\.?\d+$/;
    
    return reg.test(str);
}


const report = async (row:any) => {
  let reported_hour = prompt("请确认已学完《"+row.chapter_title+"》并填写申报学习时间，单位为小时数。")
  
  if (reported_hour != null){
    if (isFloat(reported_hour)){
      if (Number(reported_hour)>5){
        ElMessage("申报得多了点儿，少报点儿吧！")
        return false
      }
      let data = {chapter_id:row.chapter_id,course_id:row.course_id,chapter_title:row.chapter_title,sele_id:row.sele_id,reported_hour:reported_hour}
      let res = await reportLearnAPI(data)
      console.log(res)
      if(res){
        ElMessage.success("已成功申报《"+row.chapter_title+"》"+reported_hour+"小时")
        currentTableData.length=0
        getCurrentSelection()
      } else {
        ElMessage.error("出错了，请重试一次...")
      }
    } else {
      ElMessage.error("请输入整数或小数")
    }
  }
  
  
}

// 补充selection函数
const selection = async (title:string,id:number) => {
  if(confirm("确定要选择"+title+"吗？")==true){
    let data = {id:loginstate.id,courseid:id}
    let res = await selectCourseAPI(data)
    console.log(res)
    router.push('/user/mentor/')
  }
}

// 补充selection函数
const deselection = async () => {
  ElMessage.warning("不要轻言放弃，请找您的塾师咨询。")
}


// 计算属性，根据截止日期返回颜色  
const deadlineColors = computed(() => {  
  return tableData.reduce((colors:any, row:any) => {  
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
  <h5 class="centered-text">我的选课</h5>
  <el-table :data="currentTableData" style="width: 100%">
    <el-table-column label="课程名称" width="100">
      <template #default="scope">
        <el-link :href="'/course/'+scope.row.course_id" target="_blank" type="primary">{{ scope.row.course_title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column label="塾师">
      <template #default="scope">
        <el-link v-if="scope.row.shushi_id" :href="'/user/profile/'+scope.row.shushi_id" target="_blank" type="primary">{{ scope.row.shushi_name }}</el-link>
        <el-link v-else href='/user/mentor' type="primary">选塾师</el-link>
      </template>
    </el-table-column>
    <el-table-column label="章节名称">
      <template #default="scope">
        <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.chapter_title }}</el-link>
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
    <el-table-column prop="period" label="操作" width="180">
      <template #default="scope">
        <el-button link type="primary" size="small" @click="report(scope.row)">申报时间</el-button>
      </template>
    </el-table-column>
  </el-table>

  <br>
  <h5 class="centered-text">全部课程</h5>
  <el-table :data="tableData" style="width: 100%">
    <el-table-column label="课程名称" width="100">
      <template #default="scope">
        <el-link :href="'/course/'+scope.row.id" target="_blank" type="primary">{{ scope.row.title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column label="塾主">
      <template #default="scope">
        <el-link :href="'/user/profile/'+scope.row.director_id" target="_blank" type="primary">{{ scope.row.director_name }}</el-link>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="180">
      <template #default="scope">
        <el-button v-if="currentSelections.includes(scope.row.id)" link type="primary" @click="deselection()">退选</el-button>
        <el-button v-else-if="currentSelections.length<4 && loginstate.name.length>0" link type="primary" @click="selection(scope.row.title, scope.row.id)">选课</el-button>
        <span v-else>禁选</span>
      </template>
    </el-table-column>
  </el-table>
</template>

<style lang="scss" scoped>
.centered-text {
  text-align: center;
}
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