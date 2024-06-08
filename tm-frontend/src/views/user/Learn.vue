<script setup lang="ts">
import {fetchCurrentSelectionAPI, reportLearnAPI} from '../../request/course/api'
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
const currentTableData:any = reactive([])
const getCurrentSelection = async () => {
  let res = await fetchCurrentSelectionAPI()
  console.log(res)
  currentTableData.push(...res)
}
onMounted(getCurrentSelection)


function isFloat(str:string) {
    // 定义浮点数的正则表达式
    var reg = /^[-+]?(\d+)?\.\d+$/;
    
    return reg.test(str);
}

const report = async (row:any) => {
  let reported_hour = prompt("请确认已学完《"+row.chapter_title+"》并填写申报学习时间，单位为小时数。")
  
  if (reported_hour != null){
    if (isFloat(reported_hour)){
      let data = {chapter_id:row.chapter_id,course_id:row.course_id,chapter_title:row.chapter_title,sele_id:row.sele_id,reported_hour:reported_hour}
      let res = await reportLearnAPI(data)
      console.log(res)
      if(res.code==200){
        ElMessage.success("已成功申报《"+row.chapter_title+"》"+reported_hour+"小时")
        currentTableData.length=0
        getCurrentSelection()
      }
    } else {
      ElMessage.error("请输入整数或小数")
    }
  }
  
  
}

const state1 = ref('')
interface selectedChapter{
  value:string
}
const chapters = reactive<selectedChapter[]>([])
let chapterdata = [{"value":"ts"},{"value":"fastapi"},{"value":"vue3"}]
chapters.push(...chapterdata)

const querySearch = (queryString: string, cb: any) => {
  const results:any = queryString?[]:chapters
  cb(results)
}
// .chapter_title, scope.row.sele_id
</script>

<template>
  <h5>我的选课</h5>
  <el-autocomplete v-model="state1" :fetch-suggestions="querySearch" class="inline-input w-50"/>
  <el-table :data="currentTableData" style="width: 100%">
    <el-table-column prop="course_title" label="课程名称" width="180" />
    <el-table-column label="章节名称">
      <template #default="scope">
        <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.chapter_title }}</el-link>
      </template>
    </el-table-column>
    <el-table-column prop="current_serial" label="课次" />
    <el-table-column prop="deadline" label="截止日期" />
    <el-table-column prop="period" label="操作" width="180">
      <template #default="scope">
        <el-button link type="primary" size="small" @click="report(scope.row)">申报时间</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>


<style lang="scss" scoped>
</style>