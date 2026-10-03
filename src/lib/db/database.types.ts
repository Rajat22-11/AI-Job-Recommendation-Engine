// Generated from the live Supabase schema (`pnpm db:types`). Do not edit by hand.
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.18";
  };
  public: {
    Tables: {
      applications: {
        Row: {
          applied_on: string | null;
          job_id: string;
          notes: string | null;
          referral_contact: string | null;
          resume_version: string | null;
          status: string;
          updated_at: string;
        };
        Insert: {
          applied_on?: string | null;
          job_id: string;
          notes?: string | null;
          referral_contact?: string | null;
          resume_version?: string | null;
          status?: string;
          updated_at?: string;
        };
        Update: {
          applied_on?: string | null;
          job_id?: string;
          notes?: string | null;
          referral_contact?: string | null;
          resume_version?: string | null;
          status?: string;
          updated_at?: string;
        };
        Relationships: [
          {
            foreignKeyName: "applications_job_id_fkey";
            columns: ["job_id"];
            isOneToOne: true;
            referencedRelation: "job_feed";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "applications_job_id_fkey";
            columns: ["job_id"];
            isOneToOne: true;
            referencedRelation: "jobs";
            referencedColumns: ["id"];
          },
        ];
      };
      job_sources: {
        Row: {
          external_id: string | null;
          id: string;
          job_id: string;
          scraped_at: string;
          source_id: string;
          url: string;
        };
        Insert: {
          external_id?: string | null;
          id?: string;
          job_id: string;
          scraped_at?: string;
          source_id: string;
          url: string;
        };
        Update: {
          external_id?: string | null;
          id?: string;
          job_id?: string;
          scraped_at?: string;
          source_id?: string;
          url?: string;
        };
        Relationships: [
          {
            foreignKeyName: "job_sources_job_id_fkey";
            columns: ["job_id"];
            isOneToOne: false;
            referencedRelation: "job_feed";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "job_sources_job_id_fkey";
            columns: ["job_id"];
            isOneToOne: false;
            referencedRelation: "jobs";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "job_sources_source_id_fkey";
            columns: ["source_id"];
            isOneToOne: false;
            referencedRelation: "sources";
            referencedColumns: ["id"];
          },
        ];
      };
      jobs: {
        Row: {
          apply_url: string;
          company: string;
          dedupe_key: string;
          employment_type: string | null;
          first_seen_at: string;
          fit_reason: string | null;
          fit_score: number | null;
          id: string;
          is_active: boolean;
          last_seen_at: string;
          location: string | null;
          location_bucket: string | null;
          max_yoe: number | null;
          min_yoe: number | null;
          posted_at: string | null;
          role_track: string | null;
          salary_max_lpa: number | null;
          salary_meets_min: boolean | null;
          salary_min_lpa: number | null;
          salary_text: string | null;
          skills: string[];
          summary: string | null;
          title: string;
          work_mode: string | null;
        };
        Insert: {
          apply_url: string;
          company: string;
          dedupe_key: string;
          employment_type?: string | null;
          first_seen_at?: string;
          fit_reason?: string | null;
          fit_score?: number | null;
          id?: string;
          is_active?: boolean;
          last_seen_at?: string;
          location?: string | null;
          location_bucket?: string | null;
          max_yoe?: number | null;
          min_yoe?: number | null;
          posted_at?: string | null;
          role_track?: string | null;
          salary_max_lpa?: number | null;
          salary_meets_min?: boolean | null;
          salary_min_lpa?: number | null;
          salary_text?: string | null;
          skills?: string[];
          summary?: string | null;
          title: string;
          work_mode?: string | null;
        };
        Update: {
          apply_url?: string;
          company?: string;
          dedupe_key?: string;
          employment_type?: string | null;
          first_seen_at?: string;
          fit_reason?: string | null;
          fit_score?: number | null;
          id?: string;
          is_active?: boolean;
          last_seen_at?: string;
          location?: string | null;
          location_bucket?: string | null;
          max_yoe?: number | null;
          min_yoe?: number | null;
          posted_at?: string | null;
          role_track?: string | null;
          salary_max_lpa?: number | null;
          salary_meets_min?: boolean | null;
          salary_min_lpa?: number | null;
          salary_text?: string | null;
          skills?: string[];
          summary?: string | null;
          title?: string;
          work_mode?: string | null;
        };
        Relationships: [];
      };
      search_config: {
        Row: {
          excluded_companies: string[];
          id: number;
          keywords: string[];
          locations: string[];
          max_job_age_days: number;
          max_required_yoe: number;
          min_salary_lpa: number;
          updated_at: string;
        };
        Insert: {
          excluded_companies?: string[];
          id?: number;
          keywords: string[];
          locations: string[];
          max_job_age_days?: number;
          max_required_yoe?: number;
          min_salary_lpa?: number;
          updated_at?: string;
        };
        Update: {
          excluded_companies?: string[];
          id?: number;
          keywords?: string[];
          locations?: string[];
          max_job_age_days?: number;
          max_required_yoe?: number;
          min_salary_lpa?: number;
          updated_at?: string;
        };
        Relationships: [];
      };
      source_runs: {
        Row: {
          finished_at: string | null;
          id: string;
          jobs_found: number;
          jobs_new: number;
          message: string | null;
          run_id: string;
          source_id: string;
          started_at: string;
          status: string;
        };
        Insert: {
          finished_at?: string | null;
          id?: string;
          jobs_found?: number;
          jobs_new?: number;
          message?: string | null;
          run_id: string;
          source_id: string;
          started_at?: string;
          status: string;
        };
        Update: {
          finished_at?: string | null;
          id?: string;
          jobs_found?: number;
          jobs_new?: number;
          message?: string | null;
          run_id?: string;
          source_id?: string;
          started_at?: string;
          status?: string;
        };
        Relationships: [
          {
            foreignKeyName: "source_runs_source_id_fkey";
            columns: ["source_id"];
            isOneToOne: false;
            referencedRelation: "sources";
            referencedColumns: ["id"];
          },
        ];
      };
      sources: {
        Row: {
          access_method: string;
          base_url: string;
          created_at: string;
          enabled: boolean;
          id: string;
          name: string;
          notes: string | null;
          requires_login: boolean;
          search_url_template: string | null;
        };
        Insert: {
          access_method: string;
          base_url: string;
          created_at?: string;
          enabled?: boolean;
          id: string;
          name: string;
          notes?: string | null;
          requires_login?: boolean;
          search_url_template?: string | null;
        };
        Update: {
          access_method?: string;
          base_url?: string;
          created_at?: string;
          enabled?: boolean;
          id?: string;
          name?: string;
          notes?: string | null;
          requires_login?: boolean;
          search_url_template?: string | null;
        };
        Relationships: [];
      };
    };
    Views: {
      job_feed: {
        Row: {
          app_notes: string | null;
          app_status: string | null;
          applied_on: string | null;
          apply_url: string | null;
          company: string | null;
          dedupe_key: string | null;
          employment_type: string | null;
          first_seen_at: string | null;
          fit_reason: string | null;
          fit_score: number | null;
          id: string | null;
          is_active: boolean | null;
          last_seen_at: string | null;
          links: Json | null;
          location: string | null;
          location_bucket: string | null;
          max_yoe: number | null;
          min_yoe: number | null;
          posted_at: string | null;
          referral_contact: string | null;
          resume_version: string | null;
          role_track: string | null;
          salary_max_lpa: number | null;
          salary_meets_min: boolean | null;
          salary_min_lpa: number | null;
          salary_text: string | null;
          skills: string[] | null;
          summary: string | null;
          title: string | null;
          work_mode: string | null;
        };
        Relationships: [];
      };
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<
  keyof Database,
  "public"
>];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    keyof DefaultSchema["Enums"] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {},
  },
} as const;
