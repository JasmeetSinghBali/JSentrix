'use client';
// custom-components/LoginGatewayStreamingHubForm.tsx
import React, {useState} from 'react';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MaskContainer } from "@/components/ui/svg-mask-effect";
import { ColourfulText } from "@/components/ui/colourful-text";
import { motion } from "motion/react";
import { Separator } from "@/components/ui/separator";
import previewApp from "../../assets/JSentrix_Preview_home_screen_2025-08-14.gif"
import { CurrentUser, useCurrentUserStore, useGatewayAuthStore, useWsAuthStore } from '@/shared/store';
import { loginGateway, LoginGatewayTokenResponse } from '@/api/loginGateway';
import { toast } from "sonner"
import { loginStreamingHub, LoginStreamingHubTokenResponse } from '@/api/loginStreamingHub';
import { whoAmIGateway } from '@/api/whoAmIGateway';
import { MultiStepLoader } from '@/components/ui/multi-step-loader';
import indianflag from '../../assets/indian_flag.png';
import { Avatar, AvatarImage } from '@/components/ui/avatar';
import { startTokenRotation } from '@/shared/tokenService';

const loadingStates = [
  {
    text: "MCP init.", // corresponds to gateway login
  },
  {
    text: "Gateway json-rpc", // corresponds to gateway token sync zustand
  },
  {
    text: "Stream hub init.", // corresponds to streaming-hub login
  },
  {
    text: "Synching access-tokens", // corresponds to streming hub ws connection tokens sync zustand
  },
  {
    text: "Welcome to JSentrix",
  },
];

export function LoginGatewayStreamingHubForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  // 📌 Intentionally throw error to test ErrorBoundary
  // throw new Error("Test error from LoginGatewayStreamingHubForm");
  
  const [email,setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");

  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState<boolean>(false);

  const setGatewayTokens = useGatewayAuthStore(state=>state.setTokens);

  const setUser = useCurrentUserStore(state => state.setUser);

  /**
   * @desc login to gateway and streaming hub and set auth for subsequent gateway and ws connections
   * @param e (event)
   */
  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setLoading(true);
    setStep(0);
    try{
      // Step 0: login to gateway
      const TokenResponse:LoginGatewayTokenResponse | null = await loginGateway(email, password);
      setStep(1);

      if (TokenResponse !== null) {
        if(TokenResponse.access_token && TokenResponse.refresh_token){
          setGatewayTokens(TokenResponse.access_token, TokenResponse.refresh_token);
          startTokenRotation();
        }
      
        // Step 1: whoAmI
        // Immediately fetch current logged in user data
        const whoAmIGatewayResponse: CurrentUser = await whoAmIGateway(TokenResponse.access_token);
        setStep(2);

        // Step 2: wait then login to streaming hub
        await new Promise((resolve) => setTimeout(resolve, 800));
        const TokenResponseStreamingHub: LoginStreamingHubTokenResponse | null = await loginStreamingHub();
        setStep(3);

        if (TokenResponseStreamingHub !== null) {
          useWsAuthStore.getState().setAuth(
            TokenResponseStreamingHub.clientId,
            TokenResponseStreamingHub.token
          );
          setStep(4);
          // Final step — pause briefly before showing app
          await new Promise((resolve) => setTimeout(resolve, 1000));
          setUser(whoAmIGatewayResponse); // show dashboard trigger setCurrentUser zustand state RootWrapper
        }
      } 
    }catch(err: any) {
      toast.error(
          "[login-gateway-streaminghub]-Event",
          {
              description: `error: \n${JSON.stringify(err?.message || err ,null, 2)}`,
              position: 'top-center'
          }
      );
    }finally{
      setLoading(false);
      setStep(0);
    }
  };

  return (
    <React.Fragment>
      {
        loading ? 
          <MultiStepLoader loadingStates={loadingStates} loading={loading} step={step} />
        :
        (
          <div className="flex h-[40rem] w-full items-center justify-center overflow-hidden">
            <div className="h-screen w-full flex items-center justify-center relative overflow-hidden bg-black">
              <motion.img
                  src={previewApp}
                  className="h-full w-full object-contain absolute inset-0 [mask-image:radial-gradient(circle,transparent,black_80%)] pointer-events-none"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.5 }}
                  transition={{ duration: 1 }}
              />
                  <h1 className="text-md md:text-xl lg:text-4xl font-bold text-center text-white relative z-2 font-sans">
                      <ColourfulText text="JSentrix @v1.0.0" />
                  </h1>
            </div>
            <Separator orientation="vertical" />
            <MaskContainer
              revealText={
                  <div className="mx-auto max-w-4xl text-center text-md md:text-xl lg:text-4xl font-bold text-white-800 space-y-4">
                      <br/> (AGS) Agentic <span className="text-blue-500">Graph</span> System <br/>
                      <br/> <span className="text-blue-500">adaptive</span> <span className="text-blue-500">multi-agentic</span>  <br/>
                      <Separator className="w-80 my-4" />
                      <span className="text-blue-500">mcp</span> and <span className="text-blue-500">a2a</span> compliant<br/> 
                      private and local
                  </div>
              }
              className="min-h-[30rem] max-h-[40vh] text-white dark:text-black p-4 w-full max-w-4xl mx-auto"
            >
              <div className={cn("flex gap-6 max-w-lg mx-auto", className)} {...props}>
                  <Card className="w-full max-w-md mx-auto p-8">
                      <CardHeader>
                        <div className='flex flex-col items-center gap-2'>
                        <Avatar className="h-6 w-6">
                          <AvatarImage src={indianflag} alt='https://www.flaticon.com/free-icons/india' title='India icons created by Waveshade_Studios - Flaticon' />
                        </Avatar>
                        <CardTitle>JSentrix</CardTitle>
                        <CardDescription>
                          GPL-3.0 license
                        </CardDescription>
                        </div>
                      </CardHeader>
                      <CardContent>
                      <form onSubmit={handleSubmit}>
                          <div className="flex flex-col gap-6">
                              <div className="grid gap-3">
                                  <Label htmlFor="email">Email</Label>
                                  <Input
                                    id="email"
                                    type="email"
                                    placeholder="m@example.com"
                                    required
                                    onChange={e=>setEmail(e.target.value)}
                                  />
                              </div>
                          <div className="grid gap-3">
                              <div className="flex items-center">
                                <Label htmlFor="password">Password</Label>
                              </div>
                              <Input 
                                id="password" 
                                type="password" 
                                required
                                onChange={e=>setPassword(e.target.value)} 
                              />
                          </div>
                          <div className="flex flex-col gap-3">
                              <Button type="submit" className="w-full">
                                Start MCP-Client
                              </Button>
                          </div>
                          </div>
                      </form>
                      <a
                        href="https://github.com/JasmeetSinghBali"
                        className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                      >
                        (C) 2025, Jasmeet Singh Bali
                      </a>
                      </CardContent>
                  </Card>
              </div>
            </MaskContainer>
          </div>
        )
      }
    </React.Fragment>
  )
}
