<template>

  <!-- Form -->
  <span v-if="!loginstate.logined || loginstate.name.length==0">
    <el-button text @click="loginstate.dialogFormVisible = true">登录</el-button>
    <el-button text @click="registerFormVisible = true">注册</el-button>
  </span>
  
  <span v-else>
    <el-dropdown>
    <el-button text>
      {{ loginstate.name }}
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-row>
      <el-link v-if="loginstate.id==1" type="primary" href="/user/registers" target="_blank">注册列表</el-link>
    </el-row>
    <el-row>
      <el-link type="primary" href="/user/changepass" target="_blank">修改密码</el-link>
    </el-row>
    <el-row>
      <div v-if="loginstate.id==1"><el-link type="primary" href="/user/resetpass" target="_blank">重置密码</el-link></div>
    </el-row>
    <el-link type="primary" href="/user/editprofile" target="_blank">编辑个人信息</el-link>
    <br />
    <el-link type="primary" :href="'/user/profile/'+userid" target="_blank">展示个人信息</el-link>
    <br />
    <el-link type="primary" href="/user/all" target="_blank">全塾</el-link>
    <br />
    <el-link type="primary" href="/user/report" target="_blank">汇报详单</el-link>
    <br />
    <el-link type="primary" href="/user/shuzhi" target="_blank">塾值详单</el-link>
    <br />
    <el-link type="primary" href="/user/mentor" target="_blank">选塾师</el-link>
    <br />
    <el-link type="primary" href="/user/supervise" target="_blank">学习监督</el-link>
    <br />
    <el-link v-if="loginstate.id==1" type="primary" href="/course/add" target="_blank">新增课程</el-link>
    <br />
    <el-link type="primary" href="/user/followup" target="_blank">创新结项</el-link>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
    <el-button text @click="logOut">登出</el-button>
  </span>
  
  
  <el-dialog v-model="loginstate.dialogFormVisible" :width="diaglogwidth" :center="true" title="登录">
    <el-form :model="form">
      <el-form-item label="手机号" :label-width="formLabelWidth">
        <el-input v-model="form.phone" autocomplete="off" />
      </el-form-item>
      <el-form-item label="密码" :label-width="formLabelWidth">
        <el-input type="password" v-model="form.password" autocomplete="off" show-password/>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button type="primary" @click="checklogin">登录</el-button>
        <el-button @click="forgetPass">
          忘记密码
        </el-button>
      </span>
    </template>
  </el-dialog>

  <el-dialog v-model="registerFormVisible" :width="diaglogwidth" :center="true" title="注册">
    <el-form :model="formRegi" ref="ruleFormRef" :rules="rules" status-icon>
      <el-form-item label="用户名" prop="name" :label-width="formLabelWidth">
        <el-input v-model="formRegi.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="密码" prop="password" :label-width="formLabelWidth">
        <el-input v-model="formRegi.password" type="password" autocomplete="off" />
      </el-form-item>
      <el-form-item label="确认密码" prop="checkpass" :label-width="formLabelWidth">
        <el-input v-model="formRegi.checkpass" type="password" autocomplete="off" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email" :label-width="formLabelWidth">
        <el-input v-model="formRegi.email" autocomplete="off" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone" :label-width="formLabelWidth">
        <el-input v-model.number="formRegi.phone" autocomplete="off" />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button type="primary" @click="register(ruleFormRef)">注册</el-button>
      </span>
    </template>
  </el-dialog>



</template>

<script lang="ts" setup>
import { reactive,ref } from 'vue'
import { useLoginStore } from "../store";
import {loginAPI,RegisterAPI, resetPassAPI} from '../request/user/api'
import router from "../router";
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
const registerFormVisible = ref(false)
const formLabelWidth = '70px'
const diaglogwidth = '370px'
const loginstate = useLoginStore();
const userid = loginstate.id
const form = reactive({
  phone: '',
  password: '',
})

const ruleFormRef = ref<FormInstance>()
interface RuleForm {
  name: string
  password: string
  checkpass: string
  email: string
  phone: string
}

const formRegi = reactive<RuleForm>({
  name: '',
  password: '',
  checkpass: '',
  email: '',
  phone: ''
})

const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== formRegi.password) {
    console.log("密码不一致")
    console.log(rule)
    callback(new Error("密码不一致!"))
  } else {
    callback()
  }
}

const rules = reactive<FormRules<RuleForm>>({
  name: [
    { required: true, message: '请输入名字', trigger: 'blur' },
    { min: 2, max: 5, message: '长度为2到5个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码应不少于六位', trigger: 'blur' },
  ],
  checkpass: [{ validator: validatePass2, trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式错误', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3456789]\d{9}$/, message: '手机号码格式不正确', trigger: 'blur' }
  ],
})



const checklogin = async() => {
    console.log("发送请求")
    let data = {phone: form.phone, password: form.password}
    let res = await loginAPI(data)
    console.log(res);
    console.log("接收数据")
    if (res.id>0) {
      loginstate.id = res.id
      loginstate.name = res.username
      loginstate.atoken = res.atoken
      loginstate.rtoken = res.rtoken
      loginstate.logined = true
      loginstate.dialogFormVisible = false
      form.phone = ""
      form.password = ""
      window.location.reload();
    } else {
      ElMessage.error('用户名或密码错误,请重新输入')
    }
    
    
}

const logOut = () => {
  loginstate.id = 0
  loginstate.name = ""
  loginstate.atoken = "atoken"
  loginstate.rtoken = "rtoken"
  loginstate.logined = !loginstate.logined
  router.push('/')
  window.location.reload();
}

const forgetPass = async () => {
  let regex = /^1[3456789]\d{9}$/;
  let res;
  if (regex.test(form.phone)){
    let data = {phone: form.phone, password: "unkown"}
    res = await resetPassAPI(data)
  } else {
    ElMessage.error("请输入正确的手机号！")
    return false;
  }
  
  if (res && res.code == '200'){
    ElMessage.success("已收到您的第"+res.times+"次重置密码申请，会尽快为您办理！")
    loginstate.dialogFormVisible = false
    form.phone = ""
    form.password = ""
  }
}


const register = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  await formEl.validate((valid) => {
    if (valid) {
      console.log(formRegi)
      doRegister()
    } else {
      ElMessage.error('请完善注册信息!')
    }
  })
}

const doRegister = async() => {
  let data = {
    name: formRegi.name, 
    password: formRegi.password,
    email:formRegi.email,
    phone:formRegi.phone,
  }
  let res = await RegisterAPI(data)
  if (res.code == 200){
    ElMessage.success("注册成功，请等待至多三天审核！")
    formRegi.name = ''
    formRegi.password = ''
    formRegi.checkpass = ''
    formRegi.email = ''
    formRegi.phone = ''
    registerFormVisible.value = false
  } else {
    ElMessage.error("注册失败")
  }
}

</script>
<style scoped>
.el-button--text {
  margin-right: 15px;
}
.el-select {
  width: 200px;
}
.el-input {
  width: 200px;
}
.dialog-footer button:first-child {
  margin-right: 10px;
}
</style>
