// components/ui/multi-step-loader.tsx
"use client";
import { cn } from "@/lib/utils";
import { AnimatePresence, motion } from "motion/react";

const CheckIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
    className={cn("w-6 h-6", className)}
  >
    <path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
);

const CheckFilled = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={cn("w-6 h-6", className)}
  >
    <path
      fillRule="evenodd"
      d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
      clipRule="evenodd"
    />
  </svg>
);

type LoadingState = {
  text: string;
};

const LoaderCore = ({
  loadingStates,
  value = 0,
}: {
  loadingStates: LoadingState[];
  value?: number;
}) => (
  <div className="h-40 relative overflow-hidden w-full">
    <motion.div
      className="flex flex-col gap-4"
      animate={{ y: -value * 40 }} // adjust 40 based on item height
      transition={{ duration: 0.5 }}
    >
      {loadingStates.map((loadingState, index) => {
        const isCurrent = index === value;
        const isPast = index < value;
        const isFuture = index > value;

        return (
          <div
            key={index}
            className="text-left flex gap-2 items-center w-full whitespace-nowrap overflow-hidden text-ellipsis"
            style={{ height: "40px" }} // force consistent item height
          >
            <div>
              {isPast ? (
                <CheckFilled className="text-green-500" />
              ) : (
                <CheckIcon
                  className={cn(
                    isCurrent ? "text-lime-500" : "text-white/30"
                  )}
                />
              )}
            </div>
            <span
              className={cn(
                "text-md transition-all",
                isCurrent && "text-lime-500 font-semibold scale-105",
                isPast && "text-white",
                isFuture && "text-white/50"
              )}
            >
              {loadingState.text}
            </span>
          </div>
        );
      })}
    </motion.div>
  </div>
);



export const MultiStepLoader = ({
  loadingStates,
  loading,
  step,
}: {
  loadingStates: LoadingState[];
  loading?: boolean;
  step: number;
}) => {
  return (
    <AnimatePresence mode="wait">
      {loading && (
        <motion.div
          className="w-full h-full fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-2xl"
          initial={{
            opacity: 0,
          }}
          animate={{
            opacity: 1,
          }}
          exit={{
            opacity: 0,
          }}
          transition={{ duration: 0.4 }}
        >
          <div className="h-40 relative">
            <LoaderCore value={step} loadingStates={loadingStates} />
          </div>
 
          <div className="bg-gradient-to-t inset-x-0 z-20 bottom-0 bg-white dark:bg-black h-full absolute [mask-image:radial-gradient(900px_at_center,transparent_30%,white)]" />
        </motion.div>
      )}
    </AnimatePresence>
  );
};
