$(function () {
  $.getJSON('/api/v1/admin/stats?tag=user-count&callback=?', function (data) {

    $.map(data, function(entry) {
      entry[0] = Date.parse(entry[0]);
    })

    $('#user').highcharts({
      chart: {
        zoomType: 'x'
      },
      title: {
        text: 'Users Over Time'
      },
      subtitle: {
        text: 'Cumulative user count by week'
      },
      xAxis: {
        type: 'datetime'
      },
      yAxis: {
        title: {
          text: 'Users'
        }
      },
      legend: {
        enabled: false
      },
      plotOptions: {
        area: {
          fillColor: {
            linearGradient: {
              x1: 0,
              y1: 0,
              x2: 0,
              y2: 1
            },
            stops: [
              [0, Highcharts.getOptions().colors[0]],
              [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
            ]
          },
          marker: {
            radius: 2
          },
          lineWidth: 1,
          states: {
            hover: {
              lineWidth: 1
            }
          },
          threshold: null
        }
      },

      series: [{
        type: 'area',
        name: 'User Count',
        data: data
      }]
    });
  });

  $.getJSON('/api/v1/admin/stats?tag=user-created-event&callback=?', function (data) {

    $.map(data, function(entry) {
      entry[0] = Date.parse(entry[0]);
    })

    $('#created').highcharts({
      chart: {
        zoomType: 'x'
      },
      title: {
        text: 'Todo Creation Over Time'
      },
      subtitle: {
        text: 'Unique users creating at least one todo by week'
      },
      xAxis: {
        type: 'datetime'
      },
      yAxis: {
        title: {
          text: 'Users'
        }
      },
      legend: {
        enabled: false
      },
      plotOptions: {
        area: {
          fillColor: {
            linearGradient: {
              x1: 0,
              y1: 0,
              x2: 0,
              y2: 1
            },
            stops: [
              [0, Highcharts.getOptions().colors[0]],
              [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
            ]
          },
          marker: {
            radius: 2
          },
          lineWidth: 1,
          states: {
            hover: {
              lineWidth: 1
            }
          },
          threshold: null
        }
      },

      series: [{
        type: 'area',
        name: 'User Count',
        data: data
      }]
    });
  });

  $.getJSON('/api/v1/admin/stats?tag=user-engaged-event&callback=?', function (data) {

    $.map(data, function(entry) {
      entry[0] = Date.parse(entry[0]);
    })

    $('#engaged').highcharts({
      chart: {
        zoomType: 'x'
      },
      title: {
        text: 'Todo Engagement Over Time'
      },
      subtitle: {
        text: 'Unique users creating or completing at least one todo by week'
      },
      xAxis: {
        type: 'datetime'
      },
      yAxis: {
        title: {
          text: 'Users'
        }
      },
      legend: {
        enabled: false
      },
      plotOptions: {
        area: {
          fillColor: {
            linearGradient: {
              x1: 0,
              y1: 0,
              x2: 0,
              y2: 1
            },
            stops: [
              [0, Highcharts.getOptions().colors[0]],
              [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
            ]
          },
          marker: {
            radius: 2
          },
          lineWidth: 1,
          states: {
            hover: {
              lineWidth: 1
            }
          },
          threshold: null
        }
      },

      series: [{
        type: 'area',
        name: 'User Count',
        data: data
      }]
    });
  });
});
