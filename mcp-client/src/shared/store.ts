// src/shared/store.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';


// --- 1. Gateway AuthTokens ---
interface GatewayAuthState {
  accessToken: string | null;
  setAccessToken: (token: string) => void;
  clearAccessToken: () => void;

  refreshToken: string | null;
  setRefreshToken: (token: string) => void;
  clearRefreshToken: () => void;
}
export const useGatewayAuthStore = create<GatewayAuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      setAccessToken: (token) => set({ accessToken: token }),
      clearAccessToken: () => set({ accessToken: null }),

      refreshToken: null,
      setRefreshToken: (token) => set({ refreshToken: token }),
      clearRefreshToken: () => set({ refreshToken: null }),
    }),
    { name: "gateway-auth-storage" }
  )
);


// --- 2. Websocket clientId<>token store
interface WsAuthState {
  clientId: string | null;
  token: string | null;
  setAuth: (clientId: string, token: string) => void;
  clearAuth: ()=> void;
}
export const useWsAuthStore = create<WsAuthState>()(
   persist(
    (set) => ({
      clientId: null,
      token: null,
      setAuth: (clientId,token)=>set({clientId,token}),
      clearAuth: ()=> set({clientId: null, token: null})
    }),
    {
      name: 'ws-auth-storage' // key in localStorage
    }
   )
);


// ---3. Streaminges Config Store ---
type AssessmentType = "default" | "redistream";
interface StreamingesConfigState {
  assessmentType: AssessmentType;
  setAssessmentType: (value: AssessmentType) => void;

  cachingEnabled: boolean;
  setCachingEnabled: (value: boolean) => void;
}
export const useStreamingesConfigStore = create<StreamingesConfigState>()(
  persist(
    (set) => ({
      assessmentType: "default",
      setAssessmentType: (value) => set({ assessmentType: value }),

      cachingEnabled: false,
      setCachingEnabled: (value) => set({ cachingEnabled: value }),
    }),
    { name: "streaminges-config-storage" }
  )
);

// --- 4. StreamingState store ---
interface StreamingState {
  streamId: string | null;
  setStreamId: (id: string | null) => void;
  clearStreamId: () => void;

  websocketActive: boolean;
  setWebsocketActive: (state: boolean) => void;

  streamCountdown: number | null;
  setStreamCountdown: (seconds: number | null) => void;

  // AbortController to manage websocket connection
  abortController: AbortController | null;
  setAbortController: (controller: AbortController | null) => void;
}
export const useStreamingStore = create<StreamingState>()(
  (set) => ({
    streamId: null,
    setStreamId: (id) => set({ streamId: id }),
    clearStreamId: () => set({ streamId: null }),
    
    websocketActive: false,
    setWebsocketActive: (state) => set({ websocketActive: state }),
    
    streamCountdown: null,
    setStreamCountdown: (seconds) => set({ streamCountdown: seconds }),
    
    abortController: null,
    setAbortController: (controller) => set({ abortController: controller }),
  })
);

// --- 5. App router central state ---
export type AppRoute = 'dashboard' | 'analytics' | 'settings';

interface RouterState {
  currentRoute: AppRoute;
  navigate: (route: AppRoute) => void;
}

export const useRouterStore = create<RouterState>((set) => ({
  currentRoute: 'dashboard',
  navigate: (route) => set({ currentRoute: route }),
}));


// ---6. App Theme Config ---
type AppThemeType = "default" | "indie";
interface AppThemeState {
  appThemeType: AppThemeType;
  setAppThemeType: (value: AppThemeType) => void;
  
  darkModeEnabled: boolean;
  setDarkModeEnabled: (value: boolean) => void;
}
export const useAppThemeStore = create<AppThemeState>()(
  persist(
    (set) => ({
      appThemeType: "default",
      setAppThemeType: (value) => set({ appThemeType: value }),

      darkModeEnabled: false,
      setDarkModeEnabled: (value) => set({ darkModeEnabled: value }),
    }),
    { name: "app-theme-type" }
  )
);


// ---7. Current User Logged In State ---
// shud be update via the whoami route response and shud be updated by LoginForm component with whoami response 
export interface CurrentUser{
  email: string;
  full_name: string;
  employee_number: string;
  id: number;
  roles: string;
}
interface CurrentUserState {
  user: CurrentUser | null;
  setUser: (user: CurrentUser) => void;
  clearUser: () => void;
}
export const useCurrentUserStore = create<CurrentUserState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user: CurrentUser) => set({ user }),
      clearUser: () => set({ user: null }),
    }),
    { name: 'current-user' }
  )
);