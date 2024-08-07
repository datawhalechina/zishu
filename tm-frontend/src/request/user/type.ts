// 下面两个TS接口，表示要传的参数
export interface ReqLogin {
    phone: string
    password: string
}


export interface ProData {
    projects?: string;
    detail?:{code:number,message:string,data:string};
  }


export interface ItypeAPI {
    id: number,//请求的数据，用泛型
    username: string, // 返回状态码的信息，如请求成功等
    email: string, //返回后端自定义的200，404，500这种状态码
    atoken: string, 
    rtoken: string, 
}

export interface IRegister {
    name: string,
    email: string,
    password: string,
    phone: string, 
}

export interface IRegisterRes {
    code: number,
    message: string,
}

export interface IHandleRegister {
    action:string
    id:number
}

export interface IChangePass {
    newpass:string
    name:string
}

export interface IHandleResetPass {
    action:string
    id:number
}

export interface IGetProfile {
    userid:number
}

export interface IGetShumen {
    id:number
    name:string
    course_id:number
    course_title:string
}

export interface IDeleteProfile {
    filename:string
}

export interface ISubmitProfile {
    info:string
}

export interface ISaveGoal {
    goal_id:number
    content:string
    start_date:string
    deadline:string
    process:number
    review:string
    action?:string
}

export interface IEditGoaltalk {
    id:number
    counter_part_id:number
    planed_time:string
    planed_duration:number
    presenter:string
    access_info:string
}

export interface IConfirmTalk {
    id:number
    confirmer:string
}

export interface IConfirmReserve {
    shushi_id:number
    planed_time:string
    planed_duration:number
}

export interface IFinishTalk {
    id:number
    actual_duration:number
    content:string
}