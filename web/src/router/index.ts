import { createRouter, createWebHashHistory } from "vue-router";
import HomeRecords from "../views/HomeRecords.vue";
import Today from "../views/Today.vue";
import Identity from "../views/Identity.vue";
import Auth from "../views/Auth.vue";
import SocialHub from "../views/social/SocialHub.vue";
import SocialRank from "../views/social/SocialRank.vue";
import SocialPlaza from "../views/social/SocialPlaza.vue";
import SocialTeams from "../views/social/SocialTeams.vue";
import TeamChat from "../views/social/TeamChat.vue";
import TeamDetail from "../views/social/TeamDetail.vue";
import Settings from "../views/Settings.vue";
import WorkOrders from "../views/WorkOrders.vue";
import AdminUsers from "../views/AdminUsers.vue";
import { isAdmin, isLoggedIn } from "../stores/auth";

export const router = createRouter({
  // 使用 Hash 路由，提升移动端内置浏览器（如百度）刷新稳定性
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/auth", name: "auth", component: Auth, meta: { public: true } },
    { path: "/", name: "records", component: HomeRecords, meta: { title: "噜了么" } },
    { path: "/today", name: "today", component: Today, meta: { title: "今日噜么" } },
    { path: "/identity", name: "identity", component: Identity, meta: { title: "选择身份" } },
    {
      path: "/settings",
      name: "settings",
      component: Settings,
      meta: { hideTopBar: true, hideBottomNav: true },
    },
    {
      path: "/work-orders",
      name: "work-orders",
      component: WorkOrders,
      meta: { hideTopBar: true, hideBottomNav: true, title: "工单" },
    },
    {
      path: "/admin/users",
      name: "admin-users",
      component: AdminUsers,
      meta: { hideTopBar: true, hideBottomNav: true, title: "用户列表", requiresAdmin: true },
    },
    {
      path: "/social",
      component: SocialHub,
      meta: { title: "社交" },
      children: [
        { path: "", redirect: "/social/teams" },
        { path: "rank", name: "social-rank", component: SocialRank },
        { path: "plaza", name: "social-plaza", component: SocialPlaza },
        { path: "teams", name: "social-teams", component: SocialTeams },
        {
          path: "teams/:teamId/chat",
          name: "team-chat",
          component: TeamChat,
          meta: { hideTopBar: true, hideBottomNav: true, hideSubnav: true },
        },
        {
          path: "teams/:teamId/detail",
          name: "team-detail",
          component: TeamDetail,
          meta: { hideTopBar: true, hideBottomNav: true, hideSubnav: true },
        },
      ],
    },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !isLoggedIn.value) {
    return { name: "auth" };
  }
  if (to.name === "auth" && isLoggedIn.value) {
    return { name: "records" };
  }
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { name: "settings" };
  }
});
