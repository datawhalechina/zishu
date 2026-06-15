import axios from 'axios'
import { useLoginStore } from "../store";
const loginstate = useLoginStore();
// 创建axios实例
const instance = axios.create({
    baseURL: loginstate.iframeurl,// 所有的请求地址前缀部分(没有后端请求不用写)
    timeout: 80000, // 请求超时时间(毫秒)
    withCredentials: false,// 异步请求携带cookie
    headers: {
    // 设置后端需要的传参类型
    // 'Content-Type': 'application/json',
    "content-type": "application/x-www-form-urlencoded"
    // 'token': localStorage.getItem("token"),//一开始就要token
    // 'X-Requested-With': 'XMLHttpRequest',
    },
})
 
async function refreshToken() {
    const res:any = await instance.get("/api/users/refresh");
    if(res.id > 0) {
        loginstate.atoken = res.atoken;
        loginstate.rtoken = res.rtoken;
    }
    
    return res;
}

// request拦截器
instance.interceptors.request.use(
    config => {
        if (loginstate.atoken == '') {
            //添加请求头
            config.headers["token"] = loginstate.rtoken
        } else {
            config.headers["token"] = loginstate.atoken
        }
        return config
    },
    error => {
        // 对请求错误做些什么
        console.error('请求拦截器错误:', error);
        return Promise.reject(error)
    }
)

// response 拦截器
instance.interceptors.response.use(
    response => {
        // 对响应数据做点什么
        return response.data
    },
    async error => {
        // 安全修复: 添加空值检查，防止访问undefined属性
        if (!error.response) {
            // 网络错误或其他错误
            console.error('请求错误:', error.message || '网络错误');
            return Promise.reject(error);
        }
        
        const { data, config } = error.response;
        
        // 处理401错误 - token过期
        if (data?.detail?.code === 5000 && config && !config.url?.includes('/refresh')) {
            loginstate.atoken = ''
            try {
                const res = await refreshToken();
                if (res && res.id > 0) {
                    return instance(config);
                } else {
                    // 跳转登录页
                    loginstate.dialogFormVisible = true
                    //router.push(`/login?returnUrl=${router.currentRoute.value.fullPath}`)
                }
            } catch (refreshError) {
                console.error('刷新token失败:', refreshError);
                loginstate.dialogFormVisible = true
            }
        } else if (error.code === 401 || error.response?.status === 401) {
            // 跳转登录页
            loginstate.dialogFormVisible = true
            //router.push(`/login?returnUrl=${router.currentRoute.value.fullPath}`)
        }
        
        // 返回错误响应数据，如果存在
        return Promise.reject(error.response?.data || error);
    }
)
export default instance