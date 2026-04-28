/**
 * RTK Query service for read endpoints + cache-affecting mutations.
 *
 * `serverUrl` and `apiKey` are read from Redux state per-request, NOT closure-
 * captured at `createApi` time. That matters because the user can reconnect to
 * a new runtime URL at runtime, and every subsequent request must hit the new
 * server.
 *
 * Streaming endpoints (`/agents/:id/stream`, `/teams/:id/stream`) and
 * `POST /auth/token` stay imperative — they live in `@/api/client.ts`.
 */

import {
  createApi,
  fetchBaseQuery,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";
import type { z } from "zod";
import type {
  Agent,
  DeleteThreadResponse,
  LogListResponse,
  Thread,
  ThreadCreate,
  ThreadMessage,
  Tool,
  ToolListResponse,
  ToolSyncResponse,
  ToolUpdateRequest,
  TraceDetailResponse,
  TraceListResponse,
  Team,
  ResourceType,
} from "@/types/api";
import {
  AgentSchema,
  TeamSchema,
  ThreadSchema,
  ThreadMessageSchema,
  ToolListResponseSchema,
  ToolSchema,
  ToolSyncResponseSchema,
  TraceListResponseSchema,
  TraceDetailResponseSchema,
  LogListResponseSchema,
  DeleteThreadResponseSchema,
} from "@/api/schemas";
import type { AppState } from "@/store/slices/appSlice";

interface MinimalState {
  app: AppState;
}

function trimTrailingSlash(url: string): string {
  return url.replace(/\/$/, "");
}

const dynamicBaseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  const state = api.getState() as MinimalState;
  const { serverUrl, apiKey } = state.app;

  const adjustedArgs: FetchArgs =
    typeof args === "string" ? { url: args } : { ...args };

  const baseQuery = fetchBaseQuery({
    baseUrl: trimTrailingSlash(serverUrl),
    prepareHeaders: (headers) => {
      headers.set("Content-Type", "application/json");
      headers.set("Accept", "application/json");
      if (apiKey) headers.set("Authorization", `Bearer ${apiKey}`);
      return headers;
    },
  });

  return baseQuery(adjustedArgs, api, extraOptions);
};

function parser<T>(schema: z.ZodType<T>): (raw: unknown) => T {
  return (raw) => schema.parse(raw);
}

export interface ThreadQueryArgs {
  resourceType?: ResourceType;
  resourceId?: string;
  limit?: number;
}

export interface ToolQueryArgs {
  search?: string;
  source?: string;
  page?: number;
  pageSize?: number;
}

export interface TraceQueryArgs {
  limit?: number;
  offset?: number;
}

export const rtkApi = createApi({
  reducerPath: "rtkApi",
  baseQuery: dynamicBaseQuery,
  tagTypes: ["Threads", "ThreadMessages", "Tools", "Traces", "TraceDetail"],
  endpoints: (builder) => ({
    // ----- Agents / Teams ------------------------------------------------
    getAgents: builder.query<Agent[], void>({
      query: () => ({ url: "/agents" }),
      transformResponse: parser(AgentSchema.array()),
    }),
    getTeams: builder.query<Team[], void>({
      query: () => ({ url: "/teams" }),
      transformResponse: parser(TeamSchema.array()),
    }),

    // ----- Threads -------------------------------------------------------
    getThreads: builder.query<Thread[], ThreadQueryArgs>({
      query: ({ resourceType, resourceId, limit }) => {
        const params = new URLSearchParams();
        if (resourceType) params.append("resource_type", resourceType);
        if (resourceId) params.append("resource_id", resourceId);
        if (limit) params.append("limit", String(limit));
        return { url: `/threads?${params.toString()}` };
      },
      transformResponse: parser(ThreadSchema.array()),
      providesTags: ["Threads"],
    }),
    getThreadMessages: builder.query<ThreadMessage[], string>({
      query: (threadId) => ({ url: `/threads/${threadId}/messages` }),
      transformResponse: parser(ThreadMessageSchema.array()),
      providesTags: (_result, _err, threadId) => [
        { type: "ThreadMessages", id: threadId },
      ],
    }),
    createThread: builder.mutation<Thread, ThreadCreate>({
      query: (body) => ({
        url: "/threads",
        method: "POST",
        body,
      }),
      transformResponse: parser(ThreadSchema),
      invalidatesTags: ["Threads"],
    }),
    deleteThread: builder.mutation<DeleteThreadResponse, string>({
      query: (threadId) => ({
        url: `/threads/${threadId}`,
        method: "DELETE",
      }),
      transformResponse: parser(DeleteThreadResponseSchema),
      invalidatesTags: ["Threads"],
    }),

    // ----- Tools ---------------------------------------------------------
    getTools: builder.query<ToolListResponse, ToolQueryArgs>({
      query: ({ search, source, page = 1, pageSize = 50 } = {}) => {
        const params = new URLSearchParams();
        if (search) params.append("search", search);
        if (source) params.append("source", source);
        params.append("page", String(page));
        params.append("page_size", String(pageSize));
        return { url: `/tools?${params.toString()}` };
      },
      transformResponse: parser(ToolListResponseSchema),
      providesTags: ["Tools"],
    }),
    updateTool: builder.mutation<
      Tool,
      { slug: string; data: ToolUpdateRequest }
    >({
      query: ({ slug, data }) => ({
        url: `/tools/${encodeURIComponent(slug)}`,
        method: "PUT",
        body: data,
      }),
      transformResponse: parser(ToolSchema),
      invalidatesTags: ["Tools"],
    }),
    syncTools: builder.mutation<ToolSyncResponse, void>({
      query: () => ({ url: "/tools/sync", method: "POST" }),
      transformResponse: parser(ToolSyncResponseSchema),
      invalidatesTags: ["Tools"],
    }),

    // ----- Observability -------------------------------------------------
    getTraceList: builder.query<TraceListResponse, TraceQueryArgs>({
      query: ({ limit = 50, offset = 0 } = {}) => ({
        url: `/observability/traces?limit=${limit}&offset=${offset}`,
      }),
      transformResponse: parser(TraceListResponseSchema),
      providesTags: ["Traces"],
    }),
    getTraceDetail: builder.query<TraceDetailResponse, string>({
      query: (traceId) => ({ url: `/observability/traces/${traceId}` }),
      transformResponse: parser(TraceDetailResponseSchema),
      providesTags: (_r, _e, traceId) => [{ type: "TraceDetail", id: traceId }],
    }),
    getTraceLogs: builder.query<
      LogListResponse,
      { traceId: string; limit?: number }
    >({
      query: ({ traceId, limit = 500 }) => ({
        url: `/observability/traces/${traceId}/logs?limit=${limit}`,
      }),
      transformResponse: parser(LogListResponseSchema),
    }),
  }),
});

export const {
  useGetAgentsQuery,
  useGetTeamsQuery,
  useGetThreadsQuery,
  useGetThreadMessagesQuery,
  useCreateThreadMutation,
  useDeleteThreadMutation,
  useGetToolsQuery,
  useUpdateToolMutation,
  useSyncToolsMutation,
  useGetTraceListQuery,
  useGetTraceDetailQuery,
  useGetTraceLogsQuery,
} = rtkApi;
