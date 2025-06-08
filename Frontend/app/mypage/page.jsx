"use client";
import React, { useEffect, useState } from "react";
import DevImg from "../../components/Devlmg";
import { Cookies } from "react-cookie";
import { Button } from "../../components/ui/button";
import axios from "axios";
import { getUserList } from "../api";
import { postLogout } from "../api";
import { useRouter } from 'next/navigation';
import { Tabs, TabsList, TabsContent, TabsTrigger } from '@/components/ui/tabs';
// import ProjectCard from '@/components/ProjectCard';

import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/card"
import { BUILD_ID_FILE } from "next/dist/shared/lib/constants";
import { getReport } from "../api";

// export async function getUserList(user_id) {

//   try {
//     const response = await axios.get(`http://192.168.0.15:30803/dbr/get_user/${user_id}`);
//     console.log("mypage list", response)
//     return response.data;
//   } catch (error) {
//     throw new Error("Failed to fetch data: " + error.message);
//   }
// }


const Mypage = () => {
  const cookies = new Cookies();
  const router = useRouter();  // useRouter 훅 초기화


  // const [categories, setCategories] = useState(uniqueCategories);
  // const [category, setCategory] = useState('all projects');
  const [userData, setUserData] = useState(null);
  const [error, setError] = useState(null);
  const accessToken = cookies.get('access_token'); // Assuming your access token key is 'access_token'
  

  useEffect(() => {
    const checkLoginStatus = async () => {
      const user_id = cookies.get('user_id');
      if (!user_id) {
        router.push('/login'); // 로그인 되어 있지 않으면 로그인 페이지로 리다이렉트
        return;
      }
     

      try {
        const data = await getUserList(user_id);
        setUserData(data.user_info);
        cookies.set("user_uuid", data.user_info.user_uuid)
        cookies.set("user_nm", data.user_info.user_nm);
      

      } catch (error) {
        setError("Failed to fetch user data: " + error.message);
      }
    };

    checkLoginStatus();
  }, []);
  


  const handleLogout = async () => {
    try {
      const logout_formData = new FormData();
      logout_formData.append('access_token', accessToken);

      const response = await postLogout(logout_formData);   
      console.log(response);   
      if (response.logout === 'success') {
        cookies.remove('access_token'); // Remove access token from cookies
        cookies.remove('user_id'); // Remove user_id from cookies
        console.log("Logged out successfully");
        router.push('/login'); // Redirect to login page after logout
      } else {
        console.error("Logout failed:", response); // Log if logout is not successful
      }
    } catch (error) {
      console.error("Logout failed:", error.message);
    }
  };
    return (
      <section className="min-h-screen pt-12 bg-blue-100">
        <div className="container mx-auto">
          <h2 className="section-title mb-8 xl:mb-16 text-center mx-auto"> 
            My Page
          </h2>
          <div className="flex flex-col xl:flex-row">
            {/* 이미지 */}
            <div className="hidden xl:flex flex-1 relative">
              <DevImg 
                containerStyles='bg-about_shape_dark dark:bg-avout_shape_dark w-[505px] h-[505px] bg-no-repeat relative' 
                imgSrc='/mypage/mypageimg.png' 
              />
          </div>
             {/* tab */}
             <div className="flex-1">
            <Tabs defaultValue="point1">
              <TabsList className='w-full grid xl:grid-cols-3 xl:max-w-[520px] xl:border dark:border-none'>
                <TabsTrigger value='point1'>My Information</TabsTrigger>
                <TabsTrigger value='point2'>Flag</TabsTrigger>
                <TabsTrigger value='point3'>피드백</TabsTrigger>
              </TabsList>
              {/* tabs content */}
              <div className="text-lg mt-12 xl:mt-8">
                {/* point1 */}
                <TabsContent value='point1'>
                  <div className="text-center xl:text-left">
                  <Card className="w-[350px]">
                    <CardHeader>
                      <CardTitle>MY INFORMATION</CardTitle>
                      <CardDescription>Welcome to 
                      {userData && (
                        <>
                        <span>{userData.user_nm}</span> !
                        </>
                      )}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <form>
                        <div className="grid w-full items-center gap-4">
                        {userData && (
                          <>
                            <div className="flex flex-col space-y-1.5">
                              <Label htmlFor="name">Name</Label>
                              <Input id="name" placeholder={userData.user_nm} readOnly />
                            </div>
                            <div className="flex flex-col space-y-1.5">
                              <Label htmlFor="nickname">Nickname</Label>
                              <Input id="nickname" placeholder={userData.user_nicknm} readOnly />
                            </div>
                            <div className="flex flex-col space-y-1.5">
                              <Label htmlFor="gender">Gender</Label>
                              <Input id="gender" placeholder={userData.user_gender} readOnly />
                            </div>
                            <div className="flex flex-col space-y-1.5">
                              <Label htmlFor="birthday">Birthday</Label>
                              <Input id="birthday" placeholder={userData.user_birthday} readOnly />
                            </div>
                            <div className="flex flex-col space-y-1.5">
                              <Label htmlFor="tel">Phone Number</Label>
                              <Input id="tel" placeholder={userData.user_tel} readOnly />
                            </div>
                          </>
                        )}

                        
                          
                          
                  
                        </div>
                      </form>
                    </CardContent>
                    <CardFooter className="flex justify-between">
                    
                     <Button className='gap-x-2'>Update</Button>
                      <Button className='gap-x-2' onClick={handleLogout}>로그아웃</Button>

                    </CardFooter>
                  </Card>
                  
                    
                  </div>
                </TabsContent>
                <TabsContent value='point2'>
                  <div className="text-center xl:text-left">
                    <h3 className="h3 mb-4">연계 질문 Service</h3>
                    <p className="subtitle max-w-xl max-auto xl:mx-0">연계질문으로 실제 면접과 같은 느낌을 받을 수 있습니다.</p>
                  </div>
                </TabsContent>
                <TabsContent value='point3'>
                  <div className="text-center xl:text-left">
                    <h3 className="h3 mb-4">Simulation Service</h3>
                    <p className="subtitle max-w-xl max-auto xl:mx-0">예상 질문을 바탕으로 영상과 택스트 데이터 제공</p>
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </div>
        </div>
        </div>
      </section>
    )
};
export default Mypage