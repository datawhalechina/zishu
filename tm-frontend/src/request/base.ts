import axios from 'axios'
import { useLoginStore } from "../store";

// 延迟获取 store 实例，避免在 Pinia 初始化前调用
let loginstate: ReturnType<typeof useLoginStore> | null = null;
function getLoginState() {
    if (!loginstate) {
        loginstate = useLoginStore();
    }
    return loginstate;
}

// 创建axios实例
const instance = axios.create({
    baseURL: getLoginState().iframeurl,// 所有的请求地址前缀部分(没有后端请求不用写)
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
 
// 刷新token的互斥锁，防止多个请求同时触发刷新
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
    refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string) {
    refreshSubscribers.forEach(cb => cb(token));
    refreshSubscribers = [];
}

async function refreshToken() {
    const store = getLoginState();
    const res:any = await instance.get("/api/users/refresh");
    if(res.id > 0) {
        store.atoken = res.atoken;
        store.rtoken = res.rtoken;
    }
    
    return res;
}

// request拦截器
instance.interceptors.request.use(
    config => {
        const store = getLoginState();
        if (store.atoken == '') {
            //添加请求头
            config.headers["token"] = store.rtoken
        } else {
            config.headers["token"] = store.atoken
        }
        return config
    },
    error => {
        // 对请求错误做些什么
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
            return Promise.reject(error);
        }
        
        const { data, config } = error.response;
        const store = getLoginState();
        
        // 处理401错误 - token过期
        if (data?.detail?.code === 5000 && config && !config.url?.includes('/refresh')) {
            store.atoken = ''

            if (!isRefreshing) {
                isRefreshing = true;
                try {
                    const res = await refreshToken();
                    if (res && res.id > 0) {
                        onTokenRefreshed(res.atoken);
                        isRefreshing = false;
                        return instance(config);
                    } else {
                        // 跳转登录页
                        store.dialogFormVisible = true
                        isRefreshing = false;
                    }
                } catch (refreshError) {
                    store.dialogFormVisible = true
                    isRefreshing = false;
                }
            } else {
                // 正在刷新token，将请求排队等待刷新完成后重试
                return new Promise((resolve) => {
                    subscribeTokenRefresh(() => {
                        resolve(instance(config));
                    });
                });
            }
        } else if (error.code === 401 || error.response?.status === 401) {
            // 跳转登录页
            store.dialogFormVisible = true
        }
        
        // 返回错误响应数据，如果存在
        return Promise.reject(error.response?.data || error);
    }
)
export default instance
