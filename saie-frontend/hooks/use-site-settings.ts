import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/components/utils/api";

export interface SiteSettings {
  id: number;
  logo: string | null;
  bio_en: string;
  bio_ar: string;
}

const CACHE_KEY = "site_settings_cache";

const fetchSiteSettings = async (): Promise<SiteSettings> => {
  const { data } = await api.get<SiteSettings>("/site-settings/");
  localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  return data;
};

const getCachedSettings = (): SiteSettings | undefined => {
  if (typeof window === "undefined") return undefined;
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    return cached ? JSON.parse(cached) : undefined;
  } catch {
    return undefined;
  }
};

export const useSiteSettings = () => {
  return useQuery<SiteSettings, Error>({
    queryKey: ["siteSettings"],
    queryFn: fetchSiteSettings,
    initialData: getCachedSettings,
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
};

export const useUpdateSiteSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.patch<SiteSettings>("/site-settings/", formData).then((r) => r.data),
    onSuccess: (data) => {
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
      queryClient.invalidateQueries({ queryKey: ["siteSettings"] });
    },
  });
};
