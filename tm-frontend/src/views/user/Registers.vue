<script setup lang="ts">
import {fetchRigiAPI, handleRigiAPI} from '../../request/user/api'
import { onMounted, ref, reactive } from 'vue'
import { ElTable } from 'element-plus'
document.title = "注册列表"
let tableData:any = reactive([])
const doRegister = async() => {
    let res = await fetchRigiAPI()
    tableData.push(...res)
}
onMounted(doRegister)

const currentRow = ref()
const singleTableRef = ref<InstanceType<typeof ElTable>>()
interface User {
    id: number
    name: string
    email: string
    phone: string
    register_time: string
}

const handleCurrentChange = (val: User | undefined) => {
  currentRow.value = val
}

const activate_user = async ()=> {
    let msg = "确定要激活用户"+currentRow.value.name+"吗？"
    if (confirm(msg)==true) {
        console.log("激活")
        let res = await handleRigiAPI({"action":"activate", "id":currentRow.value.id})
        if (res.code == 200) {
            let index = tableData.indexOf(currentRow.value);
            if (index > -1) {
                tableData.splice(index, 1);
            }
        }
        
    }
}

const delete_user = async ()=> {
    let msg = "确定要删除用户"+currentRow.value.name+"吗？"
    if (confirm(msg)==true) {
        console.log("删除")
        let res = await handleRigiAPI({"action":"delete", "id":currentRow.value.id})
        if (res.code == 200) {
            let index = tableData.indexOf(currentRow.value);
            if (index > -1) {
                tableData.splice(index, 1);
            }
        }
    }
}

</script>

<template>
    <div v-if="currentRow">
    <el-button type="primary" @click="activate_user">激活</el-button>
    <el-button type="primary" @click="delete_user">删除</el-button>
    </div>
  <el-table 
  ref="singleTableRef"
  :data="tableData" 
  stripe 
  highlight-current-row
  style="width: 100%"
  @current-change="handleCurrentChange"
  >
    <el-table-column prop="name" label="姓名" width="180" />
    <el-table-column prop="email" label="邮箱" />
    <el-table-column prop="phone" label="手机号" />
    <el-table-column prop="register_time" label="注册时间" />
  </el-table>
</template>

<style lang="scss" scoped>
</style>