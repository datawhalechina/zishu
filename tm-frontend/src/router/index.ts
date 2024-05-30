import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
 
// 路由类型:RouteRecordRaw
const routes: Array<RouteRecordRaw> = [
  {
    path: "/",
    // 命名
    name: "index",
    component: () => import("../components/Layout.vue"),
    children: [
        {
            path: "/",
            // 首页
            name: "Home",
            component: () => import("../views/Home.vue"),
        },
        {
            path: "/learn",
            // 课程首页
            name: "Course",
            component: () => import("../views/course/Course.vue"),
        },
        {
          path: "/course/add",
          // 添加课程
          name: "Addcourse",
          component: () => import("../views/course/Add.vue"),
        },
        {
          path: "/course/:id",
          // 课程详情
          name: "Coursedetail",
          component: () => import("../views/course/Detail.vue"),
        },
        {
          path: "/course/edit/:id",
          // 编辑课程信息
          name: "Editcourse",
          component: () => import("../views/course/Edit.vue"),
       },
        {
          path: "/inno",
          // 命名
          name: "Inno",
          component: () => import("../views/inno/Project.vue"),
        },
        {
          path: "/user",
          // 用户管理
          name: "User",
          component: () => import("../views/user/Center.vue"),
        },
        {
        path: "/user/registers",
          // 注册页面
          name: "Register",
          component: () => import("../views/user/Registers.vue"),
        },
        {
          path: "/user/changepass",
          // 命名
          name: "Changepass",
          component: () => import("../views/user/Changepass.vue"),
        },
        {
          path: "/user/resetpass",
          // 命名
          name: "Resetpass",
          component: () => import("../views/user/Resetpass.vue"),
        },
        {
          path: "/user/editprofile",
            // 命名
            name: "Editprofile",
            component: () => import("../views/user/Editprofile.vue"),
        },
        {
          path: "/user/profile/:id",
            // 命名
            name: "Profile",
            component: () => import("../views/user/Profile.vue"),
        },
        {
          path: "/user/report",
          // 命名
          name: "Report",
          component: () => import("../views/user/Report.vue"),
        },
        {
          path: "/user/shuzhi",
          // 命名
          name: "Shuzhi",
          component: () => import("../views/user/Shuzhi.vue"),
        },
        {
          path: "/user/all",
          // 命名
          name: "All",
          component: () => import("../views/user/All.vue"),
        },
        {
          path: "/user/mentor",
          // 命名
          name: "Mentor",
          component: () => import("../views/user/Mentor.vue"),
        },
        {
          path: "/user/supervise",
          // 命名
          name: "Supervise",
          component: () => import("../views/user/Supervise.vue"),
        },
        {
          path: "/user/followup",
          // 命名
          name: "Followup",
          component: () => import("../views/user/Followup.vue"),
        },
    ]
  },
  
  
  
];
 
const router = createRouter({
  // 路由模式
  history: createWebHistory(),
  routes,
});
 
export default router;