export default defineAppConfig({
  pages: [
    'pages/home/index',
    'pages/forum/index',
    'pages/mine/index',
    'pages/login/index',
    'pages/register/index',
    'pages/post-detail/index',
    'pages/publish/index',
    'pages/my-activity/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#ffffff',
    navigationBarTitleText: '交易论坛',
    navigationBarTextStyle: 'black',
    backgroundColor: '#f5f6f8'
  },
  tabBar: {
    color: '#86909c',
    selectedColor: '#4e6ef2',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页'
      },
      {
        pagePath: 'pages/forum/index',
        text: '论坛'
      },
      {
        pagePath: 'pages/mine/index',
        text: '我的'
      }
    ]
  }
})
