'use client';
import React, { useState } from "react";
import { Cookies } from "react-cookie";
import { useRouter } from "next/navigation";
import { getUserList, get_kakao } from "../api";

const Login = () => {
  const [email, setEmail] = useState('');
  const cookies = new Cookies();
  const router = useRouter();


  const handleEmailChange = (event) => {
    setEmail(event.target.value);
  };

  const handleButtonClick = async (event) => {
    const url = await get_kakao();
    console.log(url)
    window.location.href = url;

  
  
     // 임시 로그인
    // const response = await getUserList("ygang4546@gmail.com");
    // cookies.set('user_id', response.user_id);
  

  }

  return (
    <div className="container max-w-sm items-center jusitfy-center">
    <div className="flex flex-col gap-3 items-center justify-center">
      <h2 className="text-xl font-semibold">로그인</h2>
      
      <form className="flex flex-col gap-5" >
        <div className="flex flex-row gap-3 items-center justify-center">
          <label className="items-center" htmlFor="email">아래의 링크를 통해 로그인해주세요!</label>
         
        </div>
        <button 
            type="button" 
            className="w-full h-12" 
            onClick={handleButtonClick}>
            <img src="/login/kakao.png" alt="Kakao Login" className="w-full h-full object-cover" />
          </button>  
          </form>
    </div>
    </div>
  
  );
};

export default Login;
