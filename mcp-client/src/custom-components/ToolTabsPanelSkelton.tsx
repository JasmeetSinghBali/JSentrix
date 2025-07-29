import { Skeleton } from "@/components/ui/skeleton";

export function SkeletonToolTabsPanel() {
  return (
    <div className="w-full">
      <div className="flex gap-2 mb-4">
        {[1, 2, 3, 4].map((_, i) => (
          <Skeleton key={i} className="h-8 w-[100px] rounded-md" />
        ))}
      </div>

      <Skeleton className="h-[200px] w-full rounded-xl" />
    </div>
  );
}
